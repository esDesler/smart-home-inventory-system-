const path = require('path');
const { pathToFileURL } = require('url');

const getBaseUrl = () => {
  if (process.env.BASE_URL) {
    return process.env.BASE_URL;
  }

  const fixturePath = path.resolve(
    __dirname,
    '..',
    'fixtures',
    'inventory.html'
  );

  return pathToFileURL(fixturePath).href;
};

module.exports = {
  getBaseUrl,
};
