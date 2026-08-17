**A. 直接删（在 ref.bib 里但正文从未引用）**
- `mascolel1995a`、`cleveland1990a`、`wooldridge2010a`、`deaton1980a`、`hyndman2018a`（带 `a` 后缀的重复条目）、`talluri2004`、`rusmevichientong2010`
- `silver2016` 在 bib 里有两份完全相同的条目，删掉重复的那份

**B. 一起删（需连同正文 `\cite` 一起删）**
- 中心性：`wasserman1994`（教科书，`freeman1977` 已够）
- 聚类：`kaufman1990`（Ward 已有 `ward1963`+`murtagh2014` 支撑）
- 风险厌恶报童：`eeckhoudt1995`
- 多品报童容量约束：`erlebacher2000`/`abdelmalek2004` 二选一，留 `abdelmalek2004`
- 选品/替代：`kok2009`（只引一次，`vanryzin1999` 同点且在问题三还用）
- 定价+库存综述：`elmaghraby2003`（只用于展望一句）
- 品类角色：`dhar2001`（只用于展望一句）
- 弹性实证：`hoch1995`（与 `tellis1988` 同点出现，后者单独还用）
- 需求互补：`deaton1980`（与 `mascolel1995` 同点，后者在 Lerner 条件处还要用）
- Shrinkage：`efron1977`（科普文，原始理论 `james1961` 已够）
- 易腐库存综述：`bakker2012`（`nahmias1982` 同点且用两处）
- 最新文献呼应：`han2026`（只在一处对照性引用）
- 伪相关：`granger1974`（与 `yule1926` 同点，留 Yule 即可）
- 定价-库存早期文献：`whitin1955`（Lerner 条件处 `mascolel1995` 已够）
- 报童原始文献：`arrow1951`（报童 4 连引 `silver2016,arrow1951,khouja1999,petruzzi1999` 减到 3 条）




绝大部分参考文献与 Crossref/OpenAlex 官方元数据一致，发现 **6 处真实错误**（都在"会印出来"的条目里）。
- `kok2007`：标题写错了。bib 是 "…application to a supermarket chain"，真实标题为 *Demand Estimation and Assortment Optimization Under Substitution: Methodology and Application*（OR, 55(6)）；页码应 1001–1021（bib 写 1007–1021）。DOI 正确。
- `rusmevichientong2012`：DOI 错误。bib 的 `10.1287/opre.1120.1045` 解析到的是 *In This Issue*（iii–vi）；正确 DOI 是 `10.1287/opre.1120.1063`，且完整标题应为 *Robust Assortment Optimization in Revenue Management Under the Multinomial Logit Choice Model*（缺 "in Revenue Management"）。
- `kok2009`：DOI 错误。bib 的 `10.1007/978-0-387-78902-6_5` 解析到的是另一章 *Category Captainship…*（79–98）；正确 DOI 是 `10.1007/978-0-387-78902-6_6`（Assortment Planning, 99–153）。
- `agrawal1996`：DOI 错误。bib 的 `…<839::AID-NAV5>3.0.CO;2-V` 解析 404；正确是 `…<839::AID-NAV4>3.0.CO;2-5`（OpenAlex 确认）。
- `yule1926`：DOI 错误。bib 的 `10.1111/j.2397-2335.1926.tb01829.x` 解析 404；正确 DOI 是 `10.2307/2341482`（JSTOR）。
- `rusmevichientong2010`：DOI 错误（`…1100.0829` → 另一篇；应为 `10.1287/opre.1100.0866`）。但是上轮删了。
