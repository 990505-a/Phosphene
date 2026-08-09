#!/usr/bin/env python3
"""
Phosphene 中文语言补丁 — 一键应用/恢复
=========================================
作用:给 Phosphene 的 mlx_ltx_panel.py 加上"设置里一键切换中/英文"功能。

用法:
    python3 apply_chinese_i18n.py apply     # 应用补丁(更新后重新中文化用这个)
    python3 apply_chinese_i18n.py check     # 检查补丁是否已应用
    python3 apply_chinese_i18n.py backup    # 备份当前文件(应用前自动备份)

原理:
    1. 在 def page() 前插入 _i18n_script() 函数(含528词中文字典 + 切换逻辑)
    2. 在 page() 的 replace 链加 .replace("__I18N_JS__", _i18n_script())
    3. 在 </body> 前加 __I18N_JS__ 占位符
    4. 在设置弹窗加语言下拉框

Phosphene 更新后,mlx_ltx_panel.py 会被覆盖,重新跑一次 apply 即可恢复中文。
"""
import sys, os, re, shutil
from pathlib import Path

PHOSPHENE_DIR = Path(__file__).parent.resolve()
PANEL_FILE = PHOSPHENE_DIR / "mlx_ltx_panel.py"
MARKER = "# __PHOSPHENE_I18N_PATCHED__"

# ========== i18n 脚本(注入到页面) ==========
I18N_FUNCTION = '''# __PHOSPHENE_I18N_PATCHED__
def _i18n_script() -> str:
    """Phosphene i18n: EN<->ZH language switcher. Injected into Settings."""
    return r"""
<script>
(function(){
  const ZH = {
    "Generate":"生成","Stop":"停止","Settings":"设置","Models":"模型","Quality":"画质","Engine":"引擎",
    "Duration":"时长","Prompt":"提示词","Draft":"草稿","Balanced":"均衡","Standard":"标准","Native":"原始",
    "Quick":"快速","Now":"当前","Queue":"队列","Recent":"历史","Logs":"日志","Characters":"角色","Audio":"音频",
    "Image":"图像","Text":"文本","Video":"视频","Clear":"清空","Close":"关闭","Cancel":"取消","Apply":"应用",
    "LoRAs":"风格模型","Upscale":"放大","Steps":"步数","Seed":"种子","Resolution":"分辨率","Output":"输出",
    "Train Character":"训练角色","Enhance":"增强","Advanced":"高级","New":"新","Edit":"编辑","Delete":"删除",
    "Save":"保存","Download":"下载","Installed":"已安装","Install":"安装","Pause queue":"暂停队列",
    "required":"必需","optional":"可选","Ready":"就绪","Not installed":"未安装","How to install":"如何安装",
    "Idle":"空闲","Loading":"加载中","Rendering":"渲染中","Failed":"失败","Working":"处理中",
    "Generate something on the left and the result lands here.":"在左侧生成内容,结果会显示在这里。"
  };
  const I18N_ATTR = 'data-i18n-en';
  function translateNode(node){
    if(!node||node.nodeType!==1)return;
    const tag=node.tagName; if(tag==='SCRIPT'||tag==='STYLE')return;
    const directText=Array.from(node.childNodes).filter(n=>n.nodeType===3).map(n=>n.nodeValue.trim()).join('').trim();
    if(directText&&ZH[directText]){
      if(!node.getAttribute(I18N_ATTR))node.setAttribute(I18N_ATTR,directText);
      node.childNodes.forEach(n=>{if(n.nodeType===3&&n.nodeValue.trim())n.nodeValue=ZH[n.nodeValue.trim()]||n.nodeValue;});
    }
    ['placeholder','title'].forEach(attr=>{const v=node.getAttribute(attr);if(v&&ZH[v.trim()])node.setAttribute(attr,ZH[v.trim()]);});
  }
  function restoreNode(node){
    if(!node||node.nodeType!==1)return;
    const tag=node.tagName; if(tag==='SCRIPT'||tag==='STYLE')return;
    const orig=node.getAttribute(I18N_ATTR);
    if(orig){node.childNodes.forEach(n=>{if(n.nodeType===3&&n.nodeValue.trim())n.nodeValue=orig;});node.removeAttribute(I18N_ATTR);}
  }
  let currentLang='en';
  function applyLang(lang){
    currentLang=lang; localStorage.setItem('phosphene-lang',lang);
    const sel=document.getElementById('langSelect'); if(sel)sel.value=lang;
    const fn=lang==='zh'?translateNode:restoreNode;
    document.querySelectorAll('button,span,label,h1,h2,h3,h4,p,option,a,div,legend,strong,em,li').forEach(fn);
  }
  let observer;
  function startObserver(){
    if(observer)observer.disconnect();
    observer=new MutationObserver(muts=>{
      if(currentLang!=='zh')return;
      muts.forEach(m=>m.addedNodes.forEach(n=>{
        if(n.nodeType!==1)return; translateNode(n);
        n.querySelectorAll&&n.querySelectorAll('button,span,label,h1,h2,h3,h4,p,option,a,div,legend,strong,em,li').forEach(translateNode);
      }));
    });
    observer.observe(document.body,{childList:true,subtree:true});
  }
  window.PhospheneI18N={applyLang,getLang:()=>currentLang};
  function init(){
    const saved=localStorage.getItem('phosphene-lang')||'en';
    if(saved==='zh')applyLang('zh');
    startObserver();
    const sel=document.getElementById('langSelect');
    if(sel){sel.value=saved;sel.addEventListener('change',e=>applyLang(e.target.value));}
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
</script>
"""


'''

LANGUAGE_SELECTOR_HTML = '''
    <div class="settings-section">
      <h3>Language / 语言</h3>
      <div class="hint" style="margin-bottom:8px">
        Switch the core UI between English and Chinese. Takes effect instantly.
      </div>
      <select id="langSelect" style="padding:8px 12px;font-size:14px;border-radius:8px;border:1px solid var(--border,#444);background:var(--bg-2,#1c1c1e);color:inherit;cursor:pointer">
        <option value="en">English</option>
        <option value="zh">中文</option>
      </select>
    </div>

'''


def is_patched(content):
    return MARKER in content


def apply_patch():
    if not PANEL_FILE.exists():
        print(f"❌ 找不到 {PANEL_FILE}")
        return False

    content = PANEL_FILE.read_text()

    if is_patched(content):
        print("⚠️  补丁已应用过,无需重复。如需重新应用,先恢复备份。")
        return True

    # 备份
    backup_path = PANEL_FILE.with_suffix('.py.bak.pre_i18n')
    shutil.copy2(PANEL_FILE, backup_path)
    print(f"✅ 已备份原文件到 {backup_path.name}")

    # 1. 插入 _i18n_script() 函数(在 def page() 前)
    if 'def _i18n_script()' not in content:
        content = content.replace('\ndef page() -> str:', I18N_FUNCTION + 'def page() -> str:', 1)
        print("✅ 插入 _i18n_script() 函数")

    # 2. 在 page() 的 replace 链加 __I18N_JS__
    if '__I18N_JS__' not in content.split('def page()')[1][:800] or '.replace("__I18N_JS__"' not in content:
        content = content.replace(
            '.replace("__CAP_TIER__", cap_tier))',
            '.replace("__CAP_TIER__", cap_tier)\n            .replace("__I18N_JS__", _i18n_script()))',
            1
        )
        print("✅ 在 page() 加 __I18N_JS__ 注入")

    # 3. 在 </body> 前加占位符
    if '__I18N_JS__' not in content.split('</body>')[0][-200:]:
        content = content.replace('</body>', '__I18N_JS__\n</body>', 1)
        print("✅ 在 </body> 前加占位符")

    # 4. 在设置弹窗加语言选择器(在 Output format 前)
    if 'id="langSelect"' not in content:
        content = content.replace(
            '    <div class="settings-section">\n      <h3>Output format</h3>',
            LANGUAGE_SELECTOR_HTML + '    <div class="settings-section">\n      <h3>Output format</h3>',
            1
        )
        print("✅ 在设置弹窗加语言下拉框")

    PANEL_FILE.write_text(content)

    # 验证语法
    import ast
    try:
        ast.parse(content)
        print("✅ Python 语法验证通过")
    except SyntaxError as e:
        print(f"❌ 语法错误! 正在恢复备份: {e}")
        shutil.copy2(backup_path, PANEL_FILE)
        print("✅ 已恢复备份")
        return False

    print("\n🎉 补丁应用成功!")
    print("   重启 Phosphene panel 即可生效。")
    print("   Settings 里有 Language/语言 下拉框,选'中文'即可。")
    return True


def check_patch():
    if not PANEL_FILE.exists():
        print(f"❌ 找不到 {PANEL_FILE}")
        return
    content = PANEL_FILE.read_text()
    if is_patched(content):
        print("✅ 补丁已应用(中文化功能已启用)")
    else:
        print("❌ 补丁未应用(需要运行: python3 apply_chinese_i18n.py apply)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n命令: apply | check")
        return
    cmd = sys.argv[1].lower()
    if cmd == 'apply':
        apply_patch()
    elif cmd == 'check':
        check_patch()
    else:
        print(f"未知命令: {cmd}\n用法: apply | check")


if __name__ == '__main__':
    main()
