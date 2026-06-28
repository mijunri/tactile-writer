#!/usr/bin/env bash
set -euo pipefail

ECS_IP="${IMJSON_ECS_IP:-118.31.57.25}"
ECS_INSTANCE_ID="${IMJSON_ECS_INSTANCE_ID:-i-bp18kchcnvcke6ltimn2}"
REGION="${ALIYUN_REGION:-cn-hangzhou}"
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"
TACTILE_API_BASE="${TACTILE_API_BASE:-http://118.31.57.25/tactile/api}"

echo "==> Deploying tactile-writer to ${ECS_IP} (${ECS_INSTANCE_ID})"

REMOTE_SCRIPT="/tmp/tactile-writer-deploy-$$.sh"
cat > "$REMOTE_SCRIPT" <<REMOTE
set -euo pipefail
DEPLOY_DIR="/opt/tactile-writer"
REPO_URL="https://github.com/mijunri/tactile-writer.git"

if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker && systemctl start docker
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
  curl -L "https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
fi

COMPOSE="docker compose"
command -v docker-compose &>/dev/null && COMPOSE="docker-compose"

mkdir -p "\$DEPLOY_DIR"
if [ -d "\$DEPLOY_DIR/.git" ]; then
  cd "\$DEPLOY_DIR" && git pull origin main
else
  git clone "\$REPO_URL" "\$DEPLOY_DIR"
  cd "\$DEPLOY_DIR"
fi

cat > .env <<ENVFILE
TACTILE_API_BASE=${TACTILE_API_BASE}
JWT_SECRET=${JWT_SECRET}
ENVFILE

\$COMPOSE down 2>/dev/null || true
\$COMPOSE build --no-cache
\$COMPOSE up -d

NGINX_CONF="/etc/nginx/conf.d/tactile-writer.conf"
if [ ! -f "\$NGINX_CONF" ]; then
  cat > "\$NGINX_CONF" <<'NGINX'
location /writer/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
}
NGINX
  nginx -t && systemctl reload nginx
fi

sleep 5
curl -sf http://127.0.0.1:8080/api/health && echo " health OK"
REMOTE

if [ -n "${SSH_KEY:-}" ] && [ -f "$SSH_KEY" ]; then
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "root@${ECS_IP}" "bash -s" < "$REMOTE_SCRIPT"
else
  SCRIPT_B64=$(base64 -w0 "$REMOTE_SCRIPT")
  python3 - "$SCRIPT_B64" "$ECS_INSTANCE_ID" "$REGION" <<'PY'
import sys, json, base64, time, os
from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.RunCommandRequest import RunCommandRequest
from aliyunsdkecs.request.v20140526.DescribeInvocationsRequest import DescribeInvocationsRequest

script_b64, instance_id, region = sys.argv[1], sys.argv[2], sys.argv[3]
client = AcsClient(os.environ['ALIYUN_ACCESS_KEY_ID'], os.environ['ALIYUN_ACCESS_KEY_SECRET'], region)

req = RunCommandRequest()
req.set_accept_format('json')
req.set_InstanceIds([instance_id])
req.set_CommandContent(script_b64)
req.set_Type('RunShellScript')
req.set_Timeout(600)
resp = json.loads(client.do_action_with_exception(req))
invoke_id = resp['InvokeId']
print(f'Cloud Assistant invoke: {invoke_id}')

for i in range(90):
    time.sleep(10)
    dr = DescribeInvocationsRequest()
    dr.set_accept_format('json')
    dr.set_InvokeId(invoke_id)
    dr.set_IncludeOutput(True)
    detail = json.loads(client.do_action_with_exception(dr))
    invocations = detail.get('Invocations', {}).get('Invocation', [])
    if not invocations:
        print('Waiting for invocation...')
        continue
    inv = invocations[0]
    status = inv.get('InvocationStatus')
    output = inv.get('Output', '')
    if output:
        try:
            print(base64.b64decode(output).decode('utf-8', errors='replace'))
        except Exception:
            print(output)
    if status in ('Success', 'Failed', 'PartialSuccess', 'Stopped'):
        print(f'Final status: {status}')
        sys.exit(0 if status == 'Success' else 1)
    print(f'Waiting... ({status}, {i+1}/90)')
PY
fi

rm -f "$REMOTE_SCRIPT"
echo ""
echo "==> Deployed! Access: http://${ECS_IP}/writer/"
