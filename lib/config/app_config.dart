/// Konfigurasi koneksi ke backend Python.
class AppConfig {
  // Ganti dengan IP/host VPS Windows tempat backend berjalan.
  static const String host = '100.78.56.14:8000';
  static const String apiKey = 'CN9-5UB1TBJMD5wM_WR5dNiPr_Gbq9CXz6dt8Pa1spg';

  static String get baseUrl => 'http://$host';
  static String get wsUrl => 'ws://$host/ws?key=$apiKey';
}
