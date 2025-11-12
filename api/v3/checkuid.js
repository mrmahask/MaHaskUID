// api/v3/checkuid.js
const fetch = require('node-fetch');
const cheerio = require('cheerio');

const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
];

const cache = new Map();

module.exports = async (req, res) => {
  const { id } = req.query;
  if (!id || !/^\d+$/.test(id) || id.length > 20) {
    return res.status(400).json({ error: 'UID không hợp lệ' });
  }

  const cacheKey = `uid:${id}`;
  if (cache.has(cacheKey)) {
    const cached = cache.get(cacheKey);
    if (Date.now() - cached.ts < 3600000) {
      return res.json({ ...cached.data, cached: true });
    }
  }

  try {
    const result = await checkUID(id);
    cache.set(cacheKey, { data: result, ts: Date.now() });
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: 'Lỗi server', details: err.message });
  }
};

async function checkUID(uid) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const pictureRes = await fetch(`https://graph.facebook.com/${uid}/picture?type=normal`, {
      redirect: 'follow',
      headers: { 'User-Agent': USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)] },
      signal: controller.signal
    });

    clearTimeout(timeout);
    const finalUrl = pictureRes.url;

    if (finalUrl.includes('static.xx.fbcdn.net') || finalUrl.includes('profile_akamai')) {
      return { uid, status: 'DIE', url: `https://www.facebook.com/${uid}`, error: 'Không tồn tại' };
    }

    const name = await getName(uid);
    return { uid, status: 'LIVE', name, url: `https://www.facebook.com/${uid}`, error: null };
  } catch (err) {
    clearTimeout(timeout);
    if (err.name === 'AbortError') {
      return { uid, status: 'DIE', url: `https://www.facebook.com/${uid}`, error: 'Timeout' };
    }
    return { uid, status: 'DIE', url: `https://www.facebook.com/${uid}`, error: 'Lỗi kết nối' };
  }
}

async function getName(uid) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const res = await fetch(`https://www.facebook.com/${uid}`, {
      headers: { 'User-Agent': USER_AGENTS[0] },
      signal: controller.signal
    });
    clearTimeout(timeout);

    const html = await res.text();
    const $ = cheerio.load(html);

    let title = $('title').text().trim();
    if (title && !title.includes('Facebook') && !title.includes('Log in')) {
      title = title.replace(/\s*[\|\-] Facebook.*$/i, '').replace(/\([^)]+\)$/, '').trim();
      if (title) return title;
    }

    const og = $('meta[property="og:title"]').attr('content');
    if (og) {
      const clean = og.replace(/\([^)]+\)$/, '').trim();
      if (clean && clean !== 'Facebook') return clean;
    }

    return 'Không lấy được tên';
  } catch (err) {
    clearTimeout(timeout);
    return 'Không lấy được tên';
  }
}
