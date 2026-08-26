# 论文检查工具位

这里保存案例级的确定性检查脚本或运行说明。脚本只读最终 PDF、源文件和结果工件，不修改原始题面、官方模板或已提交 PDF。

## 最低检查命令

~~~text
file final/paper.pdf
pdfinfo final/paper.pdf
pdftotext -layout final/paper.pdf final/paper.txt
pdftoppm -f 1 -l 3 -png -r 150 final/paper.pdf final/qa/page
shasum -a 256 final/paper.pdf
~~~

基础预检器：

~~~text
sh writing/checks/check_pdf.sh final/paper.pdf
sh writing/checks/check_pdf.sh final/paper.pdf 学校名 队员姓名 队伍编号
~~~

## 检查边界

- pdfinfo 和 pdftotext 只能证明文件可读和文本可提取，不能证明数学正确。
- 渲染检查必须人工看图；不能只依赖文本抽取。
- 页眉、匿名性、字体、Logo 和摘要页要结合当届官方模板人工核对。
- MD5/SHA-256 只用于锁定文件身份，不是内容质量证明。
