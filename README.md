# 2026 数学建模国赛（CUMCM）模拟赛

整理了部分参考资料，并作为三人协作写论文的工作仓库。

## 目录结构

```text
.
├── README.md
├── 协作规范.md
├── 资料/                      # 共享资料（只读）
│   ├── 模板/CUMCM/            # 国赛 LaTeX 模板（cumcmthesis v2.6）
│   └── 参考资料/              # Word 模板、AI 提示词、速成课讲义
└── 工作区/                    # 论文工作区
    ├── main.tex               # 主文档
    ├── sections/              # 分章节正文
    ├── code/                  # 程序源码
    ├── figures/               # 图表
    └── fonts/                 # 模板字体
```

## 快速开始

1. 安装 TeX Live / MiKTeX（需包含 `xelatex`）。
2. 进入 `工作区/`，编译 `main.tex`：

   ```bash
   xelatex main.tex
   bibtex main
   xelatex main.tex
   xelatex main.tex
   ```

   或使用 `latexmk -xelatex main.tex`。

3. 按 [协作规范.md](协作规范.md) 分工，编辑 `工作区/sections/` 下的章节文件。

## 协作

三人协作约定见 [协作规范.md](协作规范.md)。
