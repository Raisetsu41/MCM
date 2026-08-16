// 我知道这很逆天，但是。
#include <bits/stdc++.h>
#define pii pair<int, int>
#define mp(x, y) make_pair(x, y)
#define all(v) (v).begin(), (v).end()
using i128 = __int128;
using i64 = long long;
using u64 = unsigned long long;

const int ND = 1095, K = 25, M7 = 7;

struct I {
  i64 c;
  int d;
  double q, p, w, l;
};

inline void solve() {
  auto dfc = [](int y, int m, int d) -> i64 {
    y -= m <= 2;
    int e = (y >= 0 ? y : y - 399) / 400;
    unsigned ye = y - e * 400;
    unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    unsigned doe = ye * 365 + ye / 4 - ye / 100 + doy;
    return (i64)e * 146097 + doe - 719468;
  };
  auto d2i = [&](const std::string& s) -> int {
    return (int)(dfc(stoi(s.substr(0, 4)), stoi(s.substr(5, 2)), stoi(s.substr(8, 2))) - dfc(2020, 7, 1));
  };
  auto sp = [](const std::string& s) {
    std::vector<std::string> r;
    std::string t;
    for (char c : s) {
      if (c == ',') r.push_back(t), t.clear();
      else t.push_back(c);
    }
    r.push_back(t);
    return r;
  };
  auto dbl = [](const std::string& s) -> double { return s.empty() ? 0.0 : stod(s); };
  auto normcdf = [](double x) -> double { return 0.5 * erfc(-x / sqrt(2.0)); };
  auto norminv = [](double p) -> double {
    static const double a[] = {-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00}, b[] = {-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01}, c[] = {-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00}, d[] = {7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00};
    double pl = 0.02425, q, r;
    if (p < pl) {
      q = sqrt(-2 * log(p));
      return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
    }
    if (p > 1 - pl) {
      q = sqrt(-2 * log(1 - p));
      return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
    }
    q = p - 0.5, r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  };
  auto pct = [](std::vector<double> v, double q) -> double {
    std::sort(all(v));
    double pos = (v.size() - 1) * q;
    int lo = (int)floor(pos);
    return v[lo] + (pos - lo) * (v[lo + 1] - v[lo]);
  };
  auto fx = [](double v, int p) -> std::string {
    std::ostringstream o;
    o << std::fixed << std::setprecision(p) << v;
    return o.str();
  };
  auto save = [](const std::string& n, const std::string& h, const std::vector<std::vector<std::string>>& r) {
    std::ofstream o("../../results/" + n, std::ios::binary);
    o << "\xEF\xBB\xBF" << h << "\n";
    for (auto& x : r) {
      for (size_t i = 0; i < x.size(); i++) {
        if (i) o << ',';
        o << x[i];
      }
      o << "\n";
    }
  };

  
  
  auto ols = [](const std::vector<std::vector<double>>& X, const std::vector<double>& y, std::vector<double>& inv, int& n) { // OLS 回归,
    int m = (int)X[0].size(), i, j, k;
    n = (int)y.size();
    std::vector<std::vector<double>> A(m, std::vector<double>(m, 0)), I(m, std::vector<double>(m, 0));
    std::vector<double> b(m, 0), res(n, 0);
    for (i = 0; i < m; i++) I[i][i] = 1;
    for (i = 0; i < n; i++)
      for (j = 0; j < m; j++) {
        b[j] += X[i][j] * y[i];
        for (k = 0; k < m; k++) A[j][k] += X[i][j] * X[i][k];
      }
    for (j = 0; j < m; j++) {
      int p = j;
      for (i = j + 1; i < m; i++)
        if (fabs(A[i][j]) > fabs(A[p][j])) p = i;
      std::swap(A[j], A[p]), std::swap(I[j], I[p]), std::swap(b[j], b[p]);
      double dv = A[j][j];
      for (k = 0; k < m; k++) A[j][k] /= dv, I[j][k] /= dv;
      b[j] /= dv;
      for (i = 0; i < m; i++)
        if (i != j) {
          double f = A[i][j];
          for (k = 0; k < m; k++) A[i][k] -= f * A[j][k], I[i][k] -= f * I[j][k];
          b[i] -= f * b[j];
        }
    }
    double sse = 0, my = 0, mse;
    for (double v : y) my += v;
    my /= n;
    for (i = 0; i < n; i++) {
      double fit = 0;
      for (j = 0; j < m; j++) fit += X[i][j] * b[j];
      res[i] = y[i] - fit, sse += res[i] * res[i];
    }
    mse = sse / (n - m);
    inv.assign(m, 0);
    for (i = 0; i < m; i++) inv[i] = I[i][i] * mse;
    return b;
  };

  std::ifstream fi("../../results/item_daily_full.csv");
  std::string line;
  std::vector<I> rs;
  std::set<i64> cs;
  std::vector<i64> cats;
  std::map<i64, int> ci;
  std::map<i64, std::string> nm;
  std::map<i64, double> iq2, cq2, witem;
  std::map<i64, i64> icat;
  std::vector<std::vector<double>> Q, P, W, pw, wwd;
  std::vector<double> L, Lc;
  std::vector<int> wd, mo;
  int y, m, cnt, dim;
  std::vector<std::vector<double>> B, BA;
  std::vector<double> tval, r2s, inter, mse, Qb, Pb, P5, P95, m5, m95, Wb;
  std::vector<std::vector<std::string>> sc;
  std::vector<double> mopt;
  std::vector<int> anal;
  std::vector<std::vector<double>> FQ, FS;
  std::vector<std::vector<std::string>> e1, e2, e3, e4;
  std::vector<double> totQ, totP;


  auto load = [&]() {
    std::getline(fi, line);
    if ((unsigned char)line[0] == 0xEF) line = line.substr(3);
    while (std::getline(fi, line)) {
      auto f = sp(line);
      I r;
      r.c = stoll(f[11]), r.d = d2i(f[0]), r.q = dbl(f[2]), r.p = dbl(f[9]), r.w = dbl(f[15]), r.l = dbl(f[14]);
      rs.push_back(r), cs.insert(r.c);
    }
    cats.assign(all(cs));
    int ncat = (int)cats.size(), i;
    for (i = 0; i < ncat; i++) ci[cats[i]] = i;
    fi.clear(), fi.seekg(0), std::getline(fi, line);
    while (std::getline(fi, line)) {
      auto f = sp(line);
      i64 c = stoll(f[11]);
      if (!nm.count(c)) nm[c] = f[12];
    }
  };
  load();


  auto agg = [&]() { // 固定基期权重,逐日聚合
    int ncat = (int)cats.size(), i, j;
    fi.clear(), fi.seekg(0), std::getline(fi, line);
    while (std::getline(fi, line)) {
      auto f = sp(line);
      i64 it = stoll(f[1]), c = stoll(f[11]);
      icat[it] = c;
      if (d2i(f[0]) >= d2i("2022-07-01") && d2i(f[0]) <= d2i("2023-06-30")) iq2[it] += dbl(f[2]), cq2[c] += dbl(f[2]);
    }
    for (auto& kv : iq2) witem[kv.first] = kv.second / std::max(1e-12, cq2[icat[kv.first]]);
    Q.assign(ncat, std::vector<double>(ND, 0)), P.assign(ncat, std::vector<double>(ND, 0)), W.assign(ncat, std::vector<double>(ND, 0)), pw.assign(ncat, std::vector<double>(ND, 0)), wwd.assign(ncat, std::vector<double>(ND, 0)), L.assign(ncat, 0), Lc.assign(ncat, 0);
    fi.clear(), fi.seekg(0), std::getline(fi, line);
    while (std::getline(fi, line)) {
      auto f = sp(line);
      i64 it = stoll(f[1]), c = stoll(f[11]);
      int d = d2i(f[0]), cc;
      double w, qv, pv, wv;
      if (d < 0 || d >= ND) continue;
      cc = ci[c], w = witem[it], qv = dbl(f[2]), pv = dbl(f[9]), wv = dbl(f[15]);
      Q[cc][d] += qv;
      if (pv > 0) P[cc][d] += w * pv, pw[cc][d] += w;
      if (wv > 0) W[cc][d] += w * wv, wwd[cc][d] += w;
      L[cc] += dbl(f[14]), Lc[cc]++;
    }
    for (i = 0; i < ncat; i++) {
      L[i] = L[i] / Lc[i] / 100.0;
      for (j = 0; j < ND; j++) {
        if (pw[i][j] > 0) P[i][j] /= pw[i][j];
        if (wwd[i][j] > 0) W[i][j] /= wwd[i][j];
      }
    }
  };
  agg();


  auto cal = [&]() {
    int j;
    wd.assign(ND, 0), mo.assign(ND, 0), y = 2020, m = 7, cnt = 0;
    for (j = 0; j < ND; j++) {
      wd[j] = (j + 2) % 7, mo[j] = m, cnt++;
      dim = (m == 2) ? ((y % 4 == 0 && y % 100 != 0) || y % 400 == 0 ? 29 : 28) : (m == 4 || m == 6 || m == 9 || m == 11 ? 30 : 31);
      if (cnt == dim) {
        cnt = 0, m++;
        if (m == 13) m = 1, y++;
      }
    }
  };
  cal();


  auto est = [&]() { // Log-Log 弹性回归
    int ncat = (int)cats.size(), i, j, k;
    B.assign(ncat, std::vector<double>(ncat)), BA.assign(ncat, std::vector<double>(K));
    tval.assign(ncat, 0), r2s.assign(ncat, 0), inter.assign(ncat, 0), mse.assign(ncat, 0), Qb.assign(ncat, 0), Pb.assign(ncat, 0), P5.assign(ncat, 0), P95.assign(ncat, 0), m5.assign(ncat, 0), m95.assign(ncat, 0), Wb.assign(ncat, 0);
    for (int c = 0; c < ncat; c++) {
      std::vector<std::vector<double>> X;
      std::vector<double> yv;
      for (j = 0; j < ND; j++)
        if (Q[c][j] > 0 && P[c][j] > 0) {
          std::vector<double> row(K);
          for (k = 0; k < ncat; k++) row[k] = log(std::max(P[k][j], 1e-9));
          row[6] = j;
          for (k = 1; k <= 6; k++) row[6 + k] = (wd[j] == k);
          for (k = 1; k <= 11; k++) row[12 + k] = (mo[j] == k);
          row[24] = 1, X.push_back(row), yv.push_back(log(Q[c][j]));
        }
      for (j = 0; j < ND; j++)
        if (Q[c][j] > 0 && P[c][j] > 0) sc.push_back({std::to_string(cats[c]), nm[cats[c]], fx(log(P[c][j]), 4), fx(log(Q[c][j]), 4)});
      std::vector<double> inv;
      int n;
      std::vector<double> b = ols(X, yv, inv, n);
      double sse = 0, my = 0, sst = 0;
      BA[c] = b;
      for (k = 0; k < ncat; k++) B[c][k] = b[k];
      inter[c] = b[24];
      for (double v : yv) my += v;
      my /= n;
      for (i = 0; i < n; i++) {
        double fit = 0;
        for (k = 0; k < K; k++) fit += X[i][k] * b[k];
        sse += (yv[i] - fit) * (yv[i] - fit), sst += (yv[i] - my) * (yv[i] - my);
      }
      r2s[c] = 1 - sse / sst, mse[c] = sse / (n - K), tval[c] = b[c] / sqrt(inv[c]);
      std::vector<double> qv, pv, mv;
      double wcnt = 0;
      for (j = 0; j < ND; j++)
        if (Q[c][j] > 0 && P[c][j] > 0) {
          qv.push_back(Q[c][j]), pv.push_back(P[c][j]);
          if (W[c][j] > 0) mv.push_back(P[c][j] / W[c][j] - 1);
          if (j >= d2i("2023-06-24")) Wb[c] += W[c][j], wcnt++;
        }
      if (wcnt == 0)
        for (j = 0; j < ND; j++)
          if (W[c][j] > 0) Wb[c] += W[c][j], wcnt++;
      Wb[c] /= wcnt;
      Qb[c] = 0, Pb[c] = 0;
      for (double v : qv) Qb[c] += v;
      Qb[c] /= qv.size();
      for (double v : pv) Pb[c] += v;
      Pb[c] /= pv.size();
      P5[c] = pct(pv, 0.05), P95[c] = pct(pv, 0.95), m5[c] = pct(mv, 0.05), m95[c] = pct(mv, 0.95);
    }
  };
  est();


  auto price = [&]() { // 最优求加价率
    int ncat = (int)cats.size(), i;
    mopt.assign(ncat, 0), anal.assign(ncat, 0);
    for (int c = 0; c < ncat; c++) {
      double E = fabs(B[c][c]);
      double cp = Wb[c] / (1 - L[c]);
      double best = 0, bv = -1e100;
      if (E > 1) best = E / ((E - 1) * (1 - L[c])) - 1, anal[c] = 1;
      else {
        anal[c] = 0;
        for (i = 0; i <= 100; i++) {
          double mg = m5[c] + (m95[c] - m5[c]) * i / 100.0;
          double p = (1 + mg) * Wb[c];
          double v = (p - cp) * Qb[c] * pow(p / Pb[c], B[c][c]);
          if (v > bv) bv = v, best = mg;
        }
      }
      double Pstar = (1 + best) * Wb[c];
      Pstar = std::max(P5[c], std::min(P95[c], Pstar)), mopt[c] = Pstar / Wb[c] - 1;
    }
  };
  price();

  
  auto fc = [&]() { // 预测未来 7 天
    int ncat = (int)cats.size(), j, k;
    FQ.assign(ncat, std::vector<double>(M7, 0)), FS.assign(ncat, std::vector<double>(M7, 0));
    for (int c = 0; c < ncat; c++)
      for (k = 0; k < M7; k++) {
        int d = 1095 + k;
        std::vector<double> row(K);
        double lp = 0;
        for (j = 0; j < ncat; j++) row[j] = log(std::max(Pb[j], 1e-9));
        row[6] = d;
        for (j = 1; j <= 6; j++) row[6 + j] = ((d + 2) % 7 == j);
        for (j = 1; j <= 11; j++) row[12 + j] = (7 == j);
        row[24] = 1;
        for (j = 0; j < K; j++) lp += row[j] * BA[c][j];
        double qb = exp(lp + mse[c] / 2);
        FQ[c][k] = qb, FS[c][k] = qb * sqrt(exp(mse[c]) - 1);
      }
  };
  fc();


  auto nw = [&]() { // 报童
    int ncat = (int)cats.size(), k;
    totQ.assign(ncat, 0), totP.assign(ncat, 0);
    for (int c = 0; c < ncat; c++) {
      double cp = Wb[c] / (1 - L[c]);
      double Pstar = (1 + mopt[c]) * Wb[c];
      double Pstar2 = std::max(P5[c], std::min(P95[c], Pstar));
      double mstar = Pstar2 / Wb[c] - 1;
      e1.push_back({std::to_string(cats[c]), nm[cats[c]], fx(B[c][c], 4), fx(tval[c], 3), fx(r2s[c], 4), fx(inter[c], 4), fx(Pb[c], 3), fx(Qb[c], 3), fx(cp, 3), fx(m5[c], 4), fx(m95[c], 4), fx(mstar, 4), std::to_string(anal[c])});
      for (k = 0; k < M7; k++) {
        double mu = FQ[c][k] * pow(Pstar2 / Pb[c], B[c][c]), sg = FS[c][k] * pow(Pstar2 / Pb[c], B[c][c]);
        double kappa = (Pstar2 - cp) / Pstar2;
        double muL2 = log(mu * mu / sqrt(mu * mu + sg * sg)), sdL2 = sqrt(log(1 + sg * sg / (mu * mu)));
        double yy = exp(muL2 + sdL2 * norminv(kappa));
        double R = yy / (1 - L[c]), R0 = mu / (1 - L[c]);
        double emin = exp(muL2 + sdL2 * sdL2 / 2) * normcdf((log(yy) - muL2 - sdL2 * sdL2) / sdL2) + yy * (1 - normcdf((log(yy) - muL2) / sdL2));
        double ep = Pstar2 * emin - cp * yy;
        totQ[c] += R, totP[c] += ep;
        e2.push_back({std::to_string(cats[c]), nm[cats[c]], "2023-07-0" + std::to_string(k + 1), fx(FQ[c][k], 3), fx(FS[c][k], 3), fx(Pb[c], 3)});
        e3.push_back({std::to_string(cats[c]), nm[cats[c]], "2023-07-0" + std::to_string(k + 1), fx(Wb[c], 3), fx(Pstar2, 3), fx(mstar, 4), fx(mu, 3), fx(kappa, 4), fx(R, 3), fx(R0, 3), fx(ep, 2)});
      }
      e4.push_back({std::to_string(cats[c]), nm[cats[c]], fx(totQ[c], 3), fx(totP[c], 2)});
    }
    save("q2_elasticity.csv", "分类编码,分类名称,价格弹性,t值,R2,截距,参考价,参考需求,有效成本,加价率P5,加价率P95,最优加价率,是否解析解", e1);
    save("q2_forecast.csv", "分类编码,分类名称,日期,基准需求,需求标准差,参考价", e2);
    save("q2_replenishment.csv", "分类编码,分类名称,日期,批发价,最优售价,最优加价率,期望需求,临界比,补货量,确定性补货量,期望利润", e3);
    save("q2_summary.csv", "分类编码,分类名称,7天总补货量,7天总期望利润", e4);
    save("q2_scatter.csv", "分类编码,分类名称,ln价格,ln销量", sc);
  };
  nw();
}

int main() {
  solve();
  return 0;
}
