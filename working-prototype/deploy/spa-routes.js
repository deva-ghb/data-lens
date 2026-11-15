function handler(event) {
  var req = event.request;
  // Screen addresses like /roster or /warnings/3 have no file behind them: serve the app shell.
  if (req.uri.indexOf('.') === -1) { req.uri = '/index.html'; }
  return req;
}
