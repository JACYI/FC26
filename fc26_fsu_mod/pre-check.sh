#!/bin/sh
# FSU 提交前验证脚本
# 运行：bash fc26_fsu_mod/pre-check.sh
# 在 git commit 前手动运行，确保语法和测试通过

FSU_JS="fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js"
TEST_JS="fc26_fsu_mod/test_submit_cache.js"

echo "🔍 FSU 提交前验证"
echo "=================="

# 语法检查
echo ""
echo "📐 语法检查..."
if node --check "$FSU_JS"; then
    echo "   ✓ 语法通过"
else
    echo "   ❌ 语法错误！"
    exit 1
fi

# 单元测试
if [ -f "$TEST_JS" ]; then
    echo ""
    echo "🧪 单元测试..."
    if node "$TEST_JS"; then
        echo "   ✓ 测试通过"
    else
        echo "   ❌ 测试失败！"
        exit 1
    fi
fi

echo ""
echo "✅ 全部通过，可以提交"
