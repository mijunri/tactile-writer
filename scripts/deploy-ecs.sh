#!/usr/bin/env bash
set -euo pipefail

# Deploy tactile-writer to Aliyun Hangzhou ECS (imjson instance)
# Usage: IMJSON_ECS_IP=118.31.57.25 JWT_SECRET=xxx bash scripts/deploy-ecs.sh

ECS_IP="${IMJSON_ECS_IP:-118.31.57.25}"
ECS_INSTANCE_ID="${IMJSON_ECS_INSTANCE_ID:-i-bp18kchcnvcke6ltimn2}"
REGION="${ALIYUN_REGION:-cn-hangzhou}"
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"
TACTILE_API_BASE="${TACTILE_API_BASE:-http://118.31.57.25/tactile/api}"
DEPLOY_DIR="/opt/tactile-writer"
REPO_URL="https://github.com/mijunri/tactile-writer.git"

echo "==> Deploying tactile-writer to ${ECS_IP} (${ECS_INSTANCE_ID})"

DEPLOY_SCRIPT=$(cat <<'REMOTE'
set -euo pipefail
DEPLOY_DIR="/opt/tactile-writer"
REPO_URL="https://github.com/mijunri/tactile-writer.git"

if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker && systemctl start docker
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
  curl -L "https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
fi

COMPOSE="docker compose"
command -v docker-compose &>/dev/null && COMPOSE="docker-compose"

mkdir -p "$DEPLOY_DIR"
if [ -d "$DEPLOY_DIR/.git" ]; then
  cd "$DEPLOY_DIR" && git pull origin main
else
  git clone "$REPO_URL" "$DEPLOY_DIR"
  cd "$DEPLOY_DIR"
fi

cat > .env <<ENVFILE
TACTILE_API_BASE=__TACTILE_API_BASE__
JWT_SECRET=__JWT_SECRET__
ENVFILE

$COMPOSE down 2>/dev/null || true
$COMPOSE build --no-cache
$COMPOSE up -d

# nginx config for /writer/
NGINX_CONF="/etc/nginx/conf.d/tactile-writer.conf"
if [ ! -f "$NGINX_CONF" ]; then
  cat > "$NGINX_CONF" <<'NGINX'
location /writer/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
}
NGINX
  nginx -t && systemctl reload nginx
fi

sleep 3
curl -sf http://127.0.0.1:8080/api/health && echo " OK"
REMOTE
)

DEPLOY_SCRIPT="${DEPLOY_SCRIPT//__TACTILE_API_BASE__/$TACTILE_API_BASE}"
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//__JWT_SECRET__/$JWT_SECRET}"

# Try SSH first, fall back to Aliyun Cloud Assistant
if [ -n "${SSH_KEY:-}" ] && [ -f "$SSH_KEY" ]; then
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "root@${ECS_IP}" "$DEPLOY_SCRIPT"
else
  python3 <<PYEOF
import os, json, base64, time
from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.RunCommandRequest import RunCommandRequest
from aliyunsdkecs.request.v20140526.DescribeInvocationsRequest import DescribeInvocationsRequest

script = """${DEPLOY_SCRIPT}"""
client = AcsClient(os.environ['ALIYUN_ACCESS_KEY_ID'], os.environ['ALIYUN_ACCESS_KEY_SECRET'], '${REGION}')

req = RunCommandRequest()
req.set_accept_format('json')
req.set_InstanceIds(['${ECS_INSTANCE_ID}'])
req.set_CommandContent(base64.b64encode(script.encode()).decode())
req.set_Type('RunShellScript')
req.set_Timeout(600)
resp = json.loads(client.do_action_with_exception(req))
invoke_id = resp['InvokeId']
print(f'Cloud Assistant invoke: {invoke_id}')

for i in range(60):
    time.sleep(10)
    dr = DescribeInvocationsRequest()
    dr.set_accept_format('json')
    dr.set_InvokeId(invoke_id)
    dr.set_IncludeOutput(True)
    detail = json.loads(client.do_action_with_exception(dr))
    invocations = detail.get('Invocations', {}).get('Invocation', [])
    if not invocations:
        continue
    status = invocations[0].get('InvocationStatus')
    output = invocations[0].get('Output', '')
    if output:
        import base64 as b64
        try:
            print(b64.b64decode(output).decode('utf-8', errors='replace'))
        except Exception:
            print(output)
    if status in ('Success', 'Failed', 'PartialSuccess'):
        print(f'Status: {status}')
        break
    print(f'Waiting... ({status})')
PYEOF
fi

echo ""
echo "==> Deployed! Access: http://${ECS_IP}/writer/"
