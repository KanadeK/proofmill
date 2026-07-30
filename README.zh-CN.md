# ProofMill

> 在上传印刷 PDF 之前，先知道它会在哪里出问题。

[English](README.md) · [在线示例报告](https://kanadek.github.io/proofmill/) ·
[修复手册](docs/REPAIR_GUIDE.md) · [规则来源](docs/RULES.md)

ProofMill 是为自出版作者、书籍设计师和小型出版社准备的本地优先命令行工具。
它会解析真实的内页和封面 PDF，按有版本日期的 KDP 平装书规则检查，并输出
控制台、JSON 和完全离线的 HTML 报告。

它不是只有界面的空壳。扫描器实际读取：

- 页面尺寸、裁切框、出血、旋转和混合页面；
- PDF 字体资源与字体文件是否嵌入；
- 文字坐标、镜像装订线和外侧安全区；
- 图片原始像素与排版尺寸，计算有效 DPI；
- 注释、表单、JavaScript、附件、透明度和软蒙版；
- 细于 0.75 pt 的线、连续空白页和单双页规则；
- 封面展开尺寸、不同纸张/印色的书脊宽度、书脊文字限制。

## 快速开始

从 Release 下载 wheel 后安装：

```bash
python -m pip install proofmill-0.1.0-py3-none-any.whl
```

检查单个内页 PDF：

```bash
proofmill check book/interior.pdf \
  --kind interior \
  --trim 6x9 \
  --no-bleed \
  --json artifacts/report.json \
  --html artifacts/report.html
```

检查封面时必须使用最终内页页数：

```bash
proofmill check book/cover.pdf \
  --kind cover \
  --trim 6x9 \
  --pages 120 \
  --ink black \
  --paper white
```

也可以先生成配对配置：

```bash
proofmill init
proofmill audit --config proofmill.json
```

退出码 `0` 表示没有达到失败阈值的问题，`1` 表示发现阻止发布的问题，`2`
表示参数或输入不可用。

## 在 GitHub Actions 中使用

提交 `proofmill.json` 及其引用的 PDF，然后加入：

```yaml
permissions:
  contents: read

steps:
  - uses: actions/checkout@v4
  - name: Preflight print PDFs
    uses: KanadeK/proofmill@v0.1.0
    with:
      config: proofmill.json
      output-dir: artifacts/proofmill
  - name: Keep the evidence
    if: always()
    uses: actions/upload-artifact@v4
    with:
      name: proofmill-report
      path: artifacts/proofmill/
```

审计失败时，Action 会用同一退出码阻止工作流，并保留可下载的 HTML 和 JSON 证据。

## 隐私模型

ProofMill 不联网，PDF 不离开本机。报告包含文件名、SHA-256、几何信息、计数和
修复证据。越界文字只记录不可逆的短指纹与坐标，不复制未出版原稿内容。

## 真实示例与验收

仓库提交了可通过与故意损坏的 PDF 样例：

```bash
uv sync --extra dev
uv run python scripts/generate_examples.py
uv run proofmill audit --config examples/proofmill.json --output-dir artifacts/good
uv run proofmill audit --config examples/proofmill-bad.json --output-dir artifacts/bad
```

完整发布前验收只有一个入口：

```bash
uv run python scripts/verify.py
```

它会执行格式、静态检查、严格类型检查、分支覆盖率测试、样例重建、正反向 CLI
验收、确定性比较、wheel/sdist 构建、干净环境安装烟测、密钥扫描、文档生成和
Release 资产打包。

## 失败时怎么修

先查看规则：

```bash
proofmill explain IMAGE_LOW_DPI
```

再按 [docs/REPAIR_GUIDE.md](docs/REPAIR_GUIDE.md) 处理。核心原则是回到排版源文件
修复，重新导出后检查“准备上传的那个文件”，不要直接破坏性修改最终 PDF。

## 能力边界

ProofMill 与 Amazon 无关联，也不能保证平台接受或实体印刷效果。v0.1.0 不做 OCR、
PDF/X 认证、ICC/总墨量检查、字体授权判断，也不会上传或自动修改原稿。平台预览
和实体样书仍然是最终步骤。

规则、日期与官方来源见 [docs/RULES.md](docs/RULES.md)，架构见
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 许可证

[MIT](LICENSE)。Amazon、Kindle Direct Publishing、KDP、IngramSpark 等名称归
各自权利人所有。
