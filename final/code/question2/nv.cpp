#include <cmath>

extern "C" {
double normcdf(double x) { return 0.5 * std::erfc(-x / std::sqrt(2.0)); }

double norminv(double p) {
  static const double a[] = {-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00};
  static const double b[] = {-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01};
  static const double c[] = {-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00};
  static const double d[] = {7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00};
  double pl = 0.02425, q, r;
  if (p < pl) {
    q = std::sqrt(-2 * std::log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p > 1 - pl) {
    q = std::sqrt(-2 * std::log(1 - p));
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  q = p - 0.5, r = q * q;
  return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}


void newsvendor_batch(const double* mu, const double* sigma, const double* price, const double* cost, const double* loss, int n, double* y, double* kappa, double* r, double* r0, double* ep) {
  for (int i = 0; i < n; i++) {
    double m = mu[i], s = sigma[i], P = price[i], c = cost[i], L = loss[i];
    double ml = std::log(m * m / std::sqrt(m * m + s * s));
    double sl = std::sqrt(std::log(1 + s * s / (m * m)));
    double k = (P - c) / P;
    double yy = std::exp(ml + sl * norminv(k));
    double emin = std::exp(ml + sl * sl / 2) * normcdf((std::log(yy) - ml - sl * sl) / sl) + yy * (1 - normcdf((std::log(yy) - ml) / sl));
    y[i] = yy;
    kappa[i] = k;
    r[i] = yy / (1 - L);
    r0[i] = m / (1 - L);
    ep[i] = P * emin - c * yy;
  }
}

}
