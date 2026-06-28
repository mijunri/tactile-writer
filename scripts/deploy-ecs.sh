#!/usr/bin/env bash
set -euo pipefail

ECS_IP="${IMJSON_ECS_IP:-118.31.57.25}"
ECS_INSTANCE_ID="${IMJSON_ECS_INSTANCE_ID:-i-bp18kchcnvcke6ltimn2}"
REGION="${ALIYUN_REGION:-cn-hangzhou}"
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"
TACTILE_API_BASE="${TACTILE_API_BASE:-http://118.31.57.25/tactile/api}"
WRITER_PORT="${WRITER_PORT:-8082}"

echo "==> Deploying tactile-writer to ${ECS_IP}:${WRITER_PORT}"

REMOTE_SCRIPT="/tmp/tactile-writer-deploy-$$.sh"
cat > "$REMOTE_SCRIPT" <<REMOTE
set -euo pipefail
DEPLOY_DIR="/opt/tactile-writer"
REPO_URL="https://github.com/mijunri/tactile-writer.git"
WRITER_PORT=${WRITER_PORT}

echo "==> Clone or update repo"
if [ -d "\$DEPLOY_DIR/.git" ]; then
  cd "\$DEPLOY_DIR" && git pull origin main
else
  git clone "\$REPO_URL" "\$DEPLOY_DIR"
  cd "\$DEPLOY_DIR"
fi

echo "==> Backend venv"
cd "\$DEPLOY_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "==> Frontend build"
cd "\$DEPLOY_DIR/frontend"
npm install --silent
npm run build
mkdir -p "\$DEPLOY_DIR/backend/static"
cp -r dist/* "\$DEPLOY_DIR/backend/static/"

echo "==> Environment"
cat > "\$DEPLOY_DIR/backend/.env" <<ENVFILE
TACTILE_API_BASE=${TACTILE_API_BASE}
JWT_SECRET=${JWT_SECRET}
DATABASE_URL=sqlite+aiosqlite:///./data/writer.db
CORS_ORIGINS=*
ENVFILE
mkdir -p "\$DEPLOY_DIR/backend/data"

echo "==> Systemd service"
cat > /etc/systemd/system/tactile-writer.service <<UNIT
[Unit]
Description=Tactile Writer - AI Article Platform
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tactile-writer/backend
Environment=PYTHONPATH=/opt/tactile-writer/backend
EnvironmentFile=/opt/tactile-writer/backend/.env
ExecStart=/opt/tactile-writer/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${WRITER_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable tactile-writer
systemctl restart tactile-writer

echo "==> Nginx config"
NGINX_SNIPPET="/etc/nginx/snippets/tactile-writer.conf"
cat > "\$NGINX_SNIPPET" <<NGINX
    location /writer/ {
        proxy_pass http://127.0.0.1:${WRITER_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
NGINX

NGINX_SITE="/etc/nginx/sites-enabled/api.imjson.cn"
if ! grep -q "tactile-writer" "\$NGINX_SITE" 2>/dev/null; then
  sed -i '/# tactile-app-managed/i\\    # tactile-writer\\n    include /etc/nginx/snippets/tactile-writer.conf;' "\$NGINX_SITE"
  nginx -t && systemctl reload nginx
fi

sleep 3
curl -sf "http://127.0.0.1:\${WRITER_PORT}/api/health" && echo " health OK"
REMOTE

if [ -n "${SSH_KEY:-}" ] && [ -f "$SSH_KEY" ]; then
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "root@${ECS_IP}" "bash -s" < "$REMOTE_SCRIPT"
else
  python3 - "$REMOTE_SCRIPT" "$ECS_INSTANCE_ID" "$REGION" <<'PY'
import sys, json, time, os
from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.RunCommandRequest import RunCommandRequest
from aliyunsdkecs.request.v20140526.DescribeInvocationsRequest import DescribeInvocationsRequest

script_path, instance_id, region = sys.argv[1], sys.argv[2], sys.argv[3]
with open(script_path) as f:
    script = f.read()

client = AcsClient(os.environ['ALIYUN_ACCESS_KEY_ID'], os.environ['ALIYUN_ACCESS_KEY_SECRET'], region)

req = RunCommandRequest()
req.set_accept_format('json')
req.set_InstanceIds([instance_id])
req.set_CommandContent(script)
req.set_Type('RunShellScript')
req.set_Timeout(900)
resp = json.loads(client.do_action_with_exception(req))
invoke_id = resp['InvokeId']
print(f'Cloud Assistant invoke: {invoke_id}')

for i in range(120):
    time.sleep(15)
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
    instances = inv.get('InvokeInstances', {}).get('InvokeInstance', [])
    if instances:
        output = instances[0].get('Output', '')
        if output:
            import base64
            try:
                print(base64.b64decode(output).decode('utf-8', errors='replace'))
            except Exception:
                print(output)
        exit_code = instances[0].get('ExitCode')
        if status in ('Success', 'Failed', 'PartialSuccess', 'Stopped'):
            print(f'Final status: {status}, exit={exit_code}')
            sys.exit(0 if status == 'Success' else 1)
    print(f'Waiting... ({status}, {i+1}/120)')
PY
fi

rm -f "$REMOTE_SCRIPT"
echo ""
echo "==> Deployed! Access: http://${ECS_IP}/writer/"
