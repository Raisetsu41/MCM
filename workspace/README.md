# 工作区说明

论文正文、代码、图表都在这个文件夹。

## 结构

- `main.tex`：主文档，汇总章节、参考文献、附录；由统稿同学维护。
- `sections/`：按章节拆分的正文文件，每人编辑自己负责的文件。
- `code/`：程序源码，按问题命名（如 `q1_xxx.py`）。
- `figures/`：图表，按问题命名（如 `q1_xxx.pdf`）。
- `fonts/`：模板所需字体，勿动。
- `ref.bib`：参考文献库（BibTeX）。

## 编译

在本目录下执行：

```bash
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

或：

```bash
latexmk -xelatex main.tex
```