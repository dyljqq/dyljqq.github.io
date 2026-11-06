const fs = require('fs');
const path = require('path');
const http = require('http');
const assert = require('assert/strict');
const { chromium } = require('/Users/polarisdev/Documents/perfect-half/node_modules/playwright');
const root = '/Users/polarisdev/Documents/BeforeGo-Legal-quality-1106';
const evidence = path.join(root, 'docs/qa/geo-content-fix-2026-11-06');
const mime = {'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.woff2':'font/woff2','.json':'application/json'};
const results = {at:new Date().toISOString(),scope:'Two local content fixes; isolated Chromium; external requests blocked',pages:[]};
const server = http.createServer((req,res) => {
  const pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const rel = pathname.endsWith('/') ? pathname+'index.html' : pathname;
  const file = path.resolve(root,'.'+rel);
  if (!file.startsWith(root+path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {res.writeHead(404);res.end();return;}
  res.setHeader('Content-Type',mime[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  let browser;
  try {
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
    const origin='http://127.0.0.1:'+server.address().port;
    results.localOrigin=origin;
    browser=await chromium.launch({headless:true});
    const context=await browser.newContext({viewport:{width:1280,height:900},timezoneId:'Asia/Tokyo',locale:'ja-JP'});
    await context.route('**/*',route=>new URL(route.request().url()).origin===origin ? route.continue() : route.abort());
    for (const [name,route] of [['exam','/tools/ja/kyotsu-test-2027/'],['comparison','/tools/best-countdown-widget-apps-iphone/']]) {
      const page=await context.newPage();
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      await page.clock.install({time:new Date('2026-11-06T12:00:00+09:00')});
      const response=await page.goto(origin+route,{waitUntil:'networkidle'});
      assert.equal(response.status(),200);
      const record={name,path:route,status:response.status(),canonical:await page.locator('link[rel=canonical]').getAttribute('href'),views:[]};
      assert.equal(record.canonical,'https://beforego.art'+route);
      const text=await page.locator('body').innerText();
      if(name==='exam') {
        record.timetable=await page.locator('table').nth(1).locator('tbody tr').evaluateAll(rows=>rows.map(row=>[...row.querySelectorAll('th,td')].map(c=>c.textContent.trim())));
        assert.equal(record.timetable.length,8);
        for(const t of ['15:20〜16:40','17:20〜18:20','13:00〜14:10','15:00〜16:10','17:00〜18:00'])assert(text.includes(t),t);
        for(const t of ['15:10〜16:30','17:40〜19:50','受験票・写真票','前年度までの実施基準'])assert(!text.includes(t),t);
        assert(text.includes('試験開始時刻と入室終了時刻は異なります'));
        assert(text.includes('12月上旬'));
        assert(text.includes('2026年12月4日10時'));
        record.countdown=await page.locator('[data-date="2027-01-16"] [data-n]').first().textContent();
        assert.equal(record.countdown.trim(),'71');
        record.officialLinks=await page.locator('a[href^="https://www.dnc.ac.jp/"]').evaluateAll(as=>as.map(a=>a.href));
        assert(record.officialLinks.some(x=>x.includes('17475.pdf')));
        assert(record.officialLinks.some(x=>x.includes('17486.pdf')));
        assert(record.officialLinks.some(x=>x.includes('17490.pdf')));
      } else {
        for(const t of ['up to 30 routine snapshots','not a guaranteed 30 days','do not guarantee recovery','November 1 snapshot'])assert(text.includes(t),t);
        assert(!text.includes('thirty days of restore history'));
        record.currentProductLink=await page.locator('a[href="/countdown/"]').count();
        assert(record.currentProductLink>0);
      }
      record.schema=await page.locator('script[type="application/ld+json"]').evaluateAll(nodes=>nodes.map(n=>JSON.parse(n.textContent)));
      assert(record.schema.some(x=>JSON.stringify(x).includes('2026-11-06')));
      for(const [device,width,height] of [['desktop',1280,900],['mobile',375,812]]){
        await page.setViewportSize({width,height});
        if(name==='exam')await page.getByRole('heading',{name:'本試験2日間の時間割',exact:true}).scrollIntoViewIfNeeded();
        else await page.locator('h3').filter({hasText:'1. Countdown Widget: Any Event'}).scrollIntoViewIfNeeded();
        await page.screenshot({path:path.join(evidence,`${name}-${device}.png`)});
        const dimensions=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
        assert(dimensions.scrollWidth<=width,JSON.stringify(dimensions));
        record.views.push({device,...dimensions,screenshot:`${name}-${device}.png`});
      }
      assert.deepEqual(errors,[]);record.pageErrors=errors;record.pass=true;
      results.pages.push(record);await page.close();
    }
    results.pass=true;
  } catch(error) {results.pass=false;results.error=String(error.stack||error);process.exitCode=1;}
  finally {
    if(browser)await browser.close();
    await new Promise(resolve=>server.close(resolve));
    results.cleanup='browser and owned local server closed';
    fs.writeFileSync(path.join(evidence,'browser-results.json'),JSON.stringify(results,null,2)+'\n');
    console.log(JSON.stringify({pass:results.pass,pages:results.pages.map(p=>({name:p.name,pass:p.pass,views:p.views})),error:results.error,cleanup:results.cleanup}));
  }
})();
