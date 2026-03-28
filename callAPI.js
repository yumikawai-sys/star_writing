const fs = require('fs');
const path = require('https'); // 修正：前回 path に https を入れてしまっていました、正しくは以下です
const https = require('https');
const readline = require('readline'); // 入力待ち用

// --- 設定エリア ---
const TOKEN = '114671:pfpat_LYN3vy6ROEfPKF7zkd7LBZTwENCo8hFOOqUf5gXyyAk3f7RwHDTqufOJ7D7yycEUHRUIOmsxcJHP6ge9rotosiquGTyJRhpdlSl1LKZgoxURQVC5qFMwk7GLp4L40pXs';
const CSV_FILE = 'list.csv';
const OUTPUT_DIR = './output_json';
const DELAY_MS = 1500; 
const PROCESS_LIMIT = 2; // 【安全装置1】一度に処理する最大件数（テスト時は2〜5に）

if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR);

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

// ユーザーの確認を待つ関数
const confirm = (msg) => new Promise(resolve => rl.question(msg, resolve));

// API呼び出し関数
function fetchApi(url) {
    return new Promise((resolve, reject) => {
        const options = { headers: { 'Authorization': `Bearer ${TOKEN}` } };
        https.get(url, options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                if(res.statusCode === 200) resolve(JSON.parse(data));
                else reject(new Error(`Status: ${res.statusCode}`));
            });
        }).on('error', reject);
    });
}

async function start() {
    // CSV読み込み
    const content = fs.readFileSync(CSV_FILE, 'utf8');
    const lines = content.split('\n').filter(line => line.trim() !== "");
    const targets = lines.slice(1, 1 + PROCESS_LIMIT); // ヘッダーを除き、制限数だけ抽出

    console.log(`--- 実行確認 ---`);
    console.log(`CSV総行数: ${lines.length - 1}件`);
    console.log(`今回の処理上限: ${PROCESS_LIMIT}件`);
    console.log(`保存先: ${OUTPUT_DIR}`);
    
    // 【安全装置2】ユーザーが 'y' を押すまで動かない
    const answer = await confirm("実行しますか？ (y/n): ");
    if (answer.toLowerCase() !== 'y') {
        console.log("中止しました。");
        process.exit();
    }

    for (let i = 0; i < targets.length; i++) {
        const [entryId, flowId] = targets[i].split(',').map(s => s.trim());
        const url = `https://api.procedureflow.com/v1/entry-points/${entryId}/flows/${flowId}/contents`;
        const filePath = `./output_json/${flowId}.json`;

        console.log(`[${i + 1}/${targets.length}] Fetching ID: ${flowId}...`);
        
        try {
            const jsonData = await fetchApi(url);
            fs.writeFileSync(filePath, JSON.stringify(jsonData, null, 2));
            console.log(`   ✅ Success: ${flowId}.json`);
        } catch (err) {
            console.error(`   ❌ Error: ${flowId} - ${err.message}`);
        }

        // 待機
        await new Promise(r => setTimeout(r, DELAY_MS));
    }

    console.log("\nすべての処理が終わりました。");
    rl.close();
}


start().catch(err => {
    console.error("--- 致命的なエラーが発生しました ---");
    console.error(err.message);
    process.exit(1); // 異常終了したことをOSに伝える
});