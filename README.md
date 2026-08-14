# 数学建模国赛（CUMCM）LaTeX 模板与参考资料

本仓库整理全国大学生数学建模竞赛（CUMCM，以下简称「国赛」）论文写作所需的 LaTeX 模板，以及少量通用参考资料，便于备赛时直接开写、统一格式。

> 说明：本仓库只收录**国赛**相关内容，不含美赛（MCM/ICM）模板。

## 目录结构

```text
.
├── README.md
├── templates/
│   └── CUMCM/                     # 国赛 LaTeX 模板（cumcmthesis）
│       ├── 数模通用模板.tex         # 主文档，修改从这里开始
│       ├── cumcmthesis.cls         # 文档类（v2.6）
│       ├── gbt7714-numerical.bst   # GB/T 7714 参考文献样式
│       ├── ref.bib                 # BibTeX 参考文献库
│       ├── fonts/                  # 思源宋体（正文中文）
│       ├── figures/                # 示例图片
│       ├── code/                   # 示例代码（附录引用）
│       ├── YaHei.Consolas.1.11b.ttf
│       └── Fira Code Retina Nerd Font Complete.otf
└── references/                     # 通用参考资料
    ├── 2026数学建模国赛标准论文Word模板.doc
    ├── 数学建模AI提示词.pdf
    └── 速成课讲义.pdf
```

## 快速开始

### 环境要求

- TeX 发行版：TeX Live（推荐）或 MiKTeX，需包含 `xelatex`。
- 编辑器：VS Code + LaTeX Workshop、TeXstudio 等均可。
- 系统建议：Windows（模板默认调用系统楷体 `simkai.ttf`；Linux/macOS 需自行安装字体）。

### 编译

在 `templates/CUMCM` 目录下执行（模板使用 BibTeX，不是 biblatex）：

```bash
xelatex 数模通用模板.tex
bibtex  数模通用模板
xelatex 数模通用模板.tex
xelatex 数模通用模板.tex
```

也可以直接用 `latexmk`：

```bash
latexmk -xelatex 数模通用模板.tex
```

第一次编译请完整执行 4 步，以生成目录、交叉引用和参考文献。

## 模板说明

模板基于 `cumcmthesis.cls`（v2.6，2017/09/16），入口文件为 `数模通用模板.tex`。

### 文档类选项

```latex
\documentclass[withoutpreface,bwprint]{cumcmthesis}
```

| 选项 | 作用 |
| --- | --- |
| `withoutpreface` | 不生成承诺书、编号页等前置页 |
| `bwprint` | 黑白打印模式 |
| `colorprint` | 彩色模式（默认） |

### 字体配置

| 用途 | 字体 |
| --- | --- |
| 西文正文 | Times New Roman |
| 西文无衬线 | Arial |
| 中文正文（宋体） | SourceHanSerifCN（思源宋体） |
| 中文楷体 | simkai.ttf（Windows 系统楷体） |
| 等宽/代码 | YaHei.Consolas.1.11b.ttf，斜体用 Fira Code |

模板中的思源宋体与代码字体已随仓库提供；编译时请确保当前目录为 `templates/CUMCM`，否则字体按相对路径无法加载。

### 参考文献

使用 `natbib`（`numbers, sort&compress`）配合国标样式 `gbt7714-numerical.bst`，文献条目维护在 `ref.bib`：

```latex
\bibliographystyle{gbt7714-numerical}
\bibliography{ref.bib}
```

### 章节结构

模板预置了国赛论文的常见骨架，直接填空即可：

1. 摘要 + 关键词
2. 目录（默认注释，需要时打开）
3. 引言（问题背景、研究意义、问题重述）
4. 总体分析
5. 模型假设
6. 符号说明
7. 问题一至问题四：具体分析、模型准备、模型建立、模型求解
8. 模型的分析与检验（灵敏度分析、误差分析）
9. 模型的评价、改进与推广
10. 参考文献
11. 附录（文件列表、代码清单）

## 参考资料

`references/` 目录提供以下通用材料：

- `2026数学建模国赛标准论文Word模板.doc`：国赛标准 Word 模板，可用作非 LaTeX 方案或格式对照。
- `数学建模AI提示词.pdf`：AI 辅助建模与写作的提示词参考。
- `速成课讲义.pdf`：数模方法与思路的速成讲义。

## 注意事项

- **字体版权**：思源宋体（SourceHanSerifCN）与 Fira Code 为开放字体（OFL，可自由使用）；YaHei.Consolas 为改造字体，版权归原字体作者所有，仅建议本地排版使用，公开再分发前请自行确认授权。
- **仓库体积**：字体文件合计约 40 MB，克隆时可能稍慢。
- **不包含美赛模板**：如需美赛（MCM/ICM）模板，请另建仓库，不要混入本仓库。
