#!/bin/bash
# Phosphene 一键启动(不依赖 Pinokio)
# 双击此文件即可启动,自动打开浏览器
# 用法: 双击 或 bash 启动Phosphene.command

DIR=~/pinokio/api/phosphene.git
PORT=8198
URL="http://127.0.0.1:${PORT}"

G="\033[32m"; Y="\033[33m"; R="\033[31m"; B="\033[34m"; N="\033[0m"
info() { echo -e "${B}[信息]${N} $1"; }
ok()   { echo -e "${G}[完成]${N} $1"; }
warn() { echo -e "${Y}[警告]${N} $1"; }
err()  { echo -e "${R}[错误]${N} $1"; }

echo -e "${G}========================================${N}"
echo -e "${G}   Phosphene 启动器(独立版)${N}"
echo -e "${G}========================================${N}"
echo ""

# 1. 检查是否已在运行
if lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  warn "端口 ${PORT} 已被占用,Phosphene 可能已在运行"
  echo "  → 直接访问: ${URL}"
  echo "  → 如需重启: kill \$(lsof -ti tcp:${PORT})"
  read -p "  是否直接打开浏览器? (Y/n): " ans
  [ "${ans:-Y}" != "n" ] && open "${URL}"
  exit 0
fi

# 2. 检查目录
if [ ! -d "$DIR" ]; then
  err "Phosphene 目录不存在: $DIR"
  echo "  请确认 Phosphene 已安装在 ~/pinokio/api/phosphene.git"
  exit 1
fi
ok "Phosphene 目录: $DIR"

# 3. 检查 LTX 环境
if [ ! -f "$DIR/ltx-2-mlx/env/bin/python3.11" ]; then
  err "LTX Python 环境不存在"
  echo "  缺少: $DIR/ltx-2-mlx/env/bin/python3.11"
  exit 1
fi
ok "LTX 环境: ltx-2-mlx/env/bin/python3.11"

# 4. 检查 LTX 模型
LTX_MODEL="$DIR/mlx_models/ltx-2.3-mlx-q4/transformer-distilled.safetensors"
if [ -f "$LTX_MODEL" ]; then
  ok "LTX 模型: 已就绪"
else
  warn "LTX 模型缺失(可能影响 LTX 引擎,H3 不受影响)"
fi

# 5. 检查 H3 模型
H3_MODEL="$DIR/mlx_models/hailuo-h3/models/deepbeep-pruned-bf16/MiniMax-H3-FL2VA-pruned_bf16.safetensors"
if [ -f "$H3_MODEL" ]; then
  ok "H3 模型: 已就绪"
else
  warn "H3 模型缺失(可能影响 H3 引擎)"
fi
echo ""

# 6. 启动 Phosphene
info "启动 Phosphene..."
echo "  访问地址: ${URL}"
echo -e "${Y}  ⏳ 加载中(约5-10秒),请勿关闭此窗口...${N}"
echo ""

cd "$DIR"

# 后台检测就绪后自动开浏览器
(
  for i in $(seq 1 30); do
    if curl -s -m 1 "${URL}" >/dev/null 2>&1; then
      sleep 1
      open "${URL}"
      echo ""
      ok "服务已就绪,浏览器已打开: ${URL}"
      break
    fi
    sleep 1
  done
) &

# 前台运行(Ctrl+C 退出)
ltx-2-mlx/env/bin/python3.11 mlx_ltx_panel.py
