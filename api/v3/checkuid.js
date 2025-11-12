// api/v3/checkuid.js
const fetch = require('node-fetch');
const cheerio = require('cheerio');

const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
];

// Cache đơn giản (in-memory, Vercel reset mỗi deploy)
const cache = new Map();

module.exports = async (req, res) => {
  const { id } = req.query;

  if (!id || !/^\d+$/.test(id) || id.length > 20) {
    return res.status(400).json({ error: 'UID không hợp lệ' });
  }

  const cacheKey = `uid:${id}`;
  if (cache.has(cacheKey)) {
    const cached = cache.get(cacheKey);
    if (Date.now() - cached.timestamp < 3600000) { // 1 giờ
      return res.json({ ...cached.data, cached: true });
    }
  }

  try {
    const result = await checkUID(id);
    
    // Cache 1 giờ
    cache.set(cacheKey, { data: result, timestamp: Date.now() });

    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate');
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: 'Lỗi server', details: err.message });
  }
};

async function checkUID(uid) {
  const pictureUrl = `https://graph.facebook.com/${uid}/picture?type=normal`;
  
  // Kiểm tra picture redirect
  const pictureRes = await fetch(pictureUrl, {
    redirect: 'follow',
    headers: { 'User-Agent': USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)] },
    signal: AbortSignal.timeout(8000)
  }).catch(() => null);

  if (!pictureRes) {
    return { uid, status: 'DIE', url: `https://www.facebook.com/${uid}`, error: 'Timeout' };
  }

  const finalUrl = pictureRes.url;

  // DIE: ảnh mặc định
  if (finalUrl.includes('static.xx.fbcdn.net') || finalUrl.includes('profile akamai')) {
    return { uid, status: 'DIE', url: `https://www.facebook.com/${uid}`, error: 'Không tồn tại' };
  }

  // LIVE: có ảnh thật
  if (finalUrl.includes('scontent')) {
    const name = await getName(uid);
    return {
      uid,
      status: 'LIVE',
      name,
      url: `https://www.facebook.com/${uid}`,
      error: null
    };
  }

  // Fallback: coi như LIVE
  const name = await getName(uid);
  return {
    uid,
    status: 'LIVE',
    name,
    url: `https://www.facebook.com/${uid}`,
    error: null
  };
}

async function getName(uid) {
  try {
    const profileRes = await fetch(`https://www.facebook.com/${uid}`, {
      headers: { 'User-Agent': USER_AGENTS[0] },
      signal: AbortSignal.timeout(8000)
    }).catch(() => null);

    if (!profileRes) return 'Không lấy được tên';

    const html = await profileRes.text();
    const $ = cheerio.load(html);

    // Ưu tiên title
    let title = $('title').text().trim();
    if (title && !title.includes('Facebook') && !title.includes('Log in')) {
      title = title.replace(/\s*[\|\-] Facebook.*$/i, '').replace(/\([^)]+\)$/, '').trim();
      if (title) return title;
    }

    // og:title
    const ogTitle = $('meta[property="og:title"]').attr('content');
    if (ogTitle) {
      const clean = ogTitle.replace(/\([^)]+\)$/, '').trim();
      if (clean && clean !== 'Facebook') return clean;
    }

    return 'Không lấy được tên';
  } catch {
    return 'Không lấy được tên';
  }
}