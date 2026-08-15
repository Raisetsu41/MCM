# 2026 数学建模国赛（CUMCM）模拟赛

整理了部分参考资料，并作为协作写论文的工作仓库。

## 目录结构

```text
.
├── README.md
├── COLLABORATION.md
├── NOTES.md                    # 模拟赛问题记录
├── materials/                 # 共享资料（只读）
│   ├── templates/CUMCM/       # 国赛 LaTeX 模板（cumcmthesis v2.6）
│   └── references/            # Word 模板、AI 提示词、速成课讲义
├── Problem/                    # 选题与赛题数据（附件 1-4 + C 题）
└── workspace/                  # 主要工作区（建模、代码、论文都在这里）
    ├── README.md               # 工作区说明
    ├── todo.md                 # 待办事项
    ├── problem-preference.md   # 选题意愿表
    ├── main.tex                # 论文主文档
    ├── sections/               # 分章节正文
    ├── draft/                  # 建模稿与结果报告
    │   ├── ANALYSIS_0.md
    │   ├── ANALUSIS_lzy.md
    │   └── RESULTS_REPORT.md
    ├── code/                   # 程序源码
    ├── results/                # 清洗后数据与结果
    ├── figures/                # 图表
    └── fonts/                  # 模板字体
```

## 快速开始

1. 安装 TeX Live / MiKTeX（需包含 `xelatex`）。
2. 进入 `workspace/`，编译 `main.tex`：

   ```bash
   xelatex main.tex
   bibtex main
   xelatex main.tex
   xelatex main.tex
   ```

   或使用 `latexmk -xelatex main.tex`。

3. 按 [COLLABORATION.md](COLLABORATION.md) 分工，编辑 `workspace/sections/` 下的章节文件。

## 协作

协作约定见 [COLLABORATION.md](COLLABORATION.md)。
