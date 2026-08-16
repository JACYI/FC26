#!/bin/sh
# FSU C 脚本提交前验证（v2）
# 运行：bash fc26_fsu_mod/pre-check.sh
# 验证：语法（node --check）+ 全部单元测试（自动发现 test_*.js）

FSU_JS="fc26_fsu_mod/fsu-mod.c.user.js"

echo "🔍 FSU C 提交前验证"
echo "=================="

echo ""
echo "📐 语法检查..."
if node --check "$FSU_JS"; then
    echo "   ✓ 语法通过"
else
    echo "   ❌ 语法错误！"
    exit 1
fi

# 全部单元测试（含 B 的旧测试文件，回归兜底）
for T in fc26_fsu_mod/test_*.js; do
    [ -f "$T" ] || continue
    echo ""
    echo "🧪 单元测试 $(basename "$T") ..."
    if node "$T"; then
        echo "   ✓ 测试通过"
    else
        echo "   ❌ 测试失败！"
        exit 1
    fi
done

echo ""
echo "✅ 全部通过，可以提交"
