// 四种 Loop 演示台 —— 读 data.json（真实运行事件），渲染成可视化控制台。
let DATA = null, CUR = 0;

const TINT = {dialog:'#e0f5f5', goal:'#e2f5ea', scheduled:'#e2f1fb', pipeline:'#f5e8f8'};

// 控制点开关（对应 Python 的 NO_CONTROL）。true=控制点开（正常），false=关（裸奔）
const CTRL = {dialog:true, goal:true, scheduled:true, pipeline:true};
function toggleCtrl(k){ CTRL[k]=!CTRL[k]; renderMain(); }
function ctrlBar(k){
  const on=CTRL[k];
  return `<div class="ctrlbar">
    <span class="cl">控制点</span>
    <button class="switch ${on?'on':'off'}" onclick="toggleCtrl('${k}')"><span class="knob"></span></button>
    <span class="cstate ${on?'':'danger'}">${on?'开 · 正常':'关 · 裸奔（NO_CONTROL=1）'}</span>
  </div>` + (on?'':`<div class="ctrlwarn">⚠ 控制点已关闭，循环在裸奔 —— 危险行为会当场出现</div>`);
}

// 每种循环的「控制点代码」（短、清晰，带高亮）
const CODE = {
dialog:
`<span class="kw">def</span> <span class="fn">acceptance_check</span>(draft):
    <span class="kw">if</span> draft.high_risk:        <span class="cm"># 退款/投诉/索赔</span>
        <span class="kw">return</span> <span class="rd">拦下</span>, <span class="st">"强制转人工"</span>
    <span class="kw">if</span> draft.confidence &lt; <span class="st">0.6</span>:
        <span class="kw">return</span> <span class="rd">拦下</span>, <span class="st">"置信度不够"</span>
    <span class="kw">return</span> <span class="gn">放行</span>, <span class="st">"可自动发出"</span>
<span class="cm"># 模型写 draft，放行与否由清单决定</span>`,
goal:
`<span class="kw">for</span> n <span class="kw">in</span> range(max_rounds):
    <span class="kw">if</span> spent + cost &gt; budget:      <span class="cm"># 预算兜底</span>
        <span class="kw">break</span>
    cfg, claims_done = model.<span class="fn">propose</span>()
    ok, fails = <span class="fn">verifier</span>(cfg)    <span class="cm"># 独立判定</span>
    <span class="kw">if</span> ok: <span class="kw">break</span>               <span class="gn"># 只认 verifier</span>
    <span class="cm"># 模型说「我完成了」不作数</span>`,
scheduled:
`batch = <span class="fn">fetch_since</span>(cursor)     <span class="cm"># 只拉增量</span>
<span class="kw">for</span> o <span class="kw">in</span> batch:
    <span class="kw">if</span> o.id <span class="kw">in</span> seen:            <span class="cm"># 幂等键</span>
        <span class="kw">continue</span>              <span class="rd"># 重复投递→空操作</span>
    seen.<span class="fn">add</span>(o.id); <span class="fn">process</span>(o)
    cursor = max(cursor, o.seq)  <span class="gn"># 游标只前进</span>`,
pipeline:
`ok = <span class="fn">stage_assess</span>(claim)     <span class="cm"># 每步验收</span>
<span class="kw">if</span> <span class="kw">not</span> ok:
    exception_queue.<span class="fn">append</span>(claim) <span class="rd"># 转人工</span>
    <span class="kw">continue</span>
ok = <span class="fn">stage_payout</span>(claim)
<span class="kw">if</span> <span class="kw">not</span> ok:
    <span class="fn">compensate</span>(claim)       <span class="gn"># 下游失败→冲正</span>`,
};

// 每种循环的「人怎么控制」面板 —— 每个都带「控制点 开/关」开关，且可交互
function humanPanel(loop){
  const k = loop.key, on = CTRL[k];
  if(k==='dialog') return ctrlBar(k) + `
    <div class="lead">人每轮发起、每轮验收：你替客户发一句，发送前的清单当场裁决 —— 能自答就自答，命中高风险就转人工。</div>
    <div class="tryrow">
      <input id="dlgInput" class="tryin" placeholder="替客户发一句：我要退款 / 订单A2381到了吗"
             onkeydown="if(event.key==='Enter')tryDialog()">
      <button class="btn ok" onclick="tryDialog()">发一条</button>
    </div>
    <div id="dlgOut" class="tryout"></div>
    <div class="hint2">${on?'清单：高风险意图→转人工 · 置信度&lt;0.6→不自答 · 「转人工」入口永远可用'
                          :'⚠ 清单已关：不管你发什么（含「我要退款」）都会被自动发出去。'}</div>`;
  if(k==='goal') return ctrlBar(k) + `
    <div class="lead">人只在两端：给目标 + 预算，中间不干预。改预算，看结局怎么变（达标，还是超预算止损）。</div>
    <div class="kv"><span class="k">目标（可机判）</span><span class="v">port=8080 · timeout=30 · retries=3</span></div>
    <div class="kv"><span class="k">完成判据</span><span class="v">${on?'独立 verifier 全绿（每轮 0.25）':'⚠ 已关：信模型自述'}</span></div>
    <div class="tryrow"><span class="tlabel">预算上限</span>
      <button class="pbtn" onclick="tryGoal(1.0,this)">1.0</button>
      <button class="pbtn" onclick="tryGoal(0.6,this)">0.6</button>
      <button class="pbtn" onclick="tryGoal(0.4,this)">0.4</button>
    </div>
    <div id="goalOut" class="tryout"></div>`;
  if(k==='scheduled') return ctrlBar(k) + `
    <div class="lead">人退到环外，只复核被标记的大额。游标和幂等键都落库，重启不重算、重复投递不二次入账。</div>
    <div class="kv"><span class="k">游标 cursor（已落库）</span><span class="v">seq = 5</span></div>
    <div class="kv"><span class="k">幂等键集合 seen</span><span class="v">{A001..A005}</span></div>
    <div class="subttl">大额待人工复核</div>` + (on ? `
    <div class="eqitem"><span class="info">A002　<b>¥8600 大额</b></span>
      <span class="btns"><button class="btn ok" onclick="review(this)">复核通过</button><button class="btn no" onclick="review(this,'驳回')">驳回</button></span></div>
    <div class="eqitem"><span class="info">A005　<b>¥12000 大额</b></span>
      <span class="btns"><button class="btn ok" onclick="review(this)">复核通过</button><button class="btn no" onclick="review(this,'驳回')">驳回</button></span></div>` : `
    <div class="dangerbox">⚠ 控制点已关：A002(¥8600)、A005(¥12000) 无人复核，直接自动入账；重复投递也会二次入账。</div>`);
  if(k==='pipeline') return ctrlBar(k) + `
    <div class="lead">人从操作者变成例外处理者：不点任何一步的「继续」，只裁决被拦下的这几件。</div>
    <div class="subttl">例外队列 · 待人工裁决</div>` + (on ? `
    <div class="eqitem"><span class="info">C03　<b>¥60000 超上限</b></span>
      <span class="btns"><button class="btn ok" onclick="resolveExc(this,'放行')">放行</button><button class="btn no" onclick="resolveExc(this,'驳回')">驳回</button></span></div>
    <div class="eqitem"><span class="info">C04　<b>置信度 0.55 偏低</b></span>
      <span class="btns"><button class="btn ok" onclick="resolveExc(this,'放行')">放行</button><button class="btn no" onclick="resolveExc(this,'驳回')">驳回</button></span></div>
    <div class="kv" style="margin-top:8px"><span class="k">自动结案</span><span class="v">2 件</span></div>` : `
    <div class="dangerbox">⚠ 控制点已关：C03(¥60000 超上限)、C04(低置信) 无人裁决，直接自动打款/理算 —— 坏 case 一路执行到底。</div>`);
  return '';
}

function renderRail(){
  const rail = document.getElementById('rail');
  rail.innerHTML = `<div class="rail-title">四种循环 · 按「人的位置」</div>` +
    DATA.loops.map((l,i)=>`
      <div class="tab ${i===CUR?'on':''}" style="--tab-c:${l.color}" onclick="select(${i})">
        <div class="num" style="--tab-c:${l.color}">${l.name.slice(0,1)}</div>
        <div><div class="nm">${l.name.slice(1)}</div><div class="who">${l.human.split('：')[0]}</div></div>
      </div>`).join('') +
    `<div class="rail-foot">人退得越远，<b>要补的配置越多</b>。<br>四种没有先进落后 —— 匹配任务才对。</div>`;
}

function traceHTML(events){
  let out = '', rows = '', ti = 0;
  const flush = (tick)=>{ if(tick!==null){ out += `<div class="tickcard" data-ti="${ti++}">${tick}${rows}</div>`; rows=''; } };
  let curTick = null;
  for(const e of events){
    if(e.t==='banner') continue;
    if(e.t==='tick'){ flush(curTick); curTick = `<div class="tick-h"><span class="rnd">第 ${e.n} 圈</span><span class="note">${e.note||''}</span></div>`; }
    else if(e.t==='step'){ rows += `<div class="row"><span class="lab">${e.label}</span><span class="val">${e.value}</span></div>`; }
    else if(e.t==='gate'){ rows += `<div class="verdict ${e.passed?'pass':'fail'}"><span class="ic">${e.passed?'✔':'✘'}</span><span>${e.passed?'放行':'拦下'} · ${e.reason}</span></div>`; }
    else if(e.t==='escalate'){ rows += `<div class="verdict esc"><span class="ic">⇢</span><span>转人工 · ${e.reason}</span></div>`; }
    else if(e.t==='close'){ rows += `<div class="closeline">${e.note||''}</div>`; }
    else if(e.t==='summary'){ /* handled separately */ }
  }
  flush(curTick);
  return out;
}

function summaryHTML(events){
  const s = events.find(e=>e.t==='summary');
  if(!s) return '';
  return `<div class="statstrip"><div class="st-h">本轮小结</div><ul>` +
    s.lines.map((l,i)=>`<li class="${i===s.lines.length-1?'warn':''}">${l}</li>`).join('') +
    `</ul></div>`;
}

function renderMain(){
  const l = DATA.loops[CUR];
  const m = document.getElementById('main');
  document.documentElement.style.setProperty('--accent', l.color);
  document.documentElement.style.setProperty('--accent-bg', TINT[l.key]);
  m.innerHTML = `
    <div class="loop-head">
      <span class="big">${l.name}</span>
      <span class="badge control"><span class="dot" style="background:${l.color}"></span>控制点：${l.control}</span>
      <span class="badge case">真实案例 · ${l.case} · ${l.case_stat}</span>
      <div class="sub">${l.control_sub}</div>
    </div>
    <div class="grid">
      <div class="card trace">
        <div class="card-h"><span class="ttl">运行轨迹 · 每一圈都看得见</span>
          <span class="tracebtns"><button class="tbtn" onclick="replay()">▶ 重放一圈圈</button><button class="tbtn ghost" onclick="showAll()">展开全部</button></span></div>
        <div class="card-b" id="traceBody">${traceHTML(l.events)}</div>
      </div>
      <div>
        <div class="card codecard">
          <div class="card-h"><span class="ttl">控制点代码</span><span class="hint">${l.file}</span></div>
          <div class="code">${CODE[l.key]}</div>
        </div>
        <div class="card human" style="margin-top:16px">
          <div class="card-h"><span class="ttl">人怎么控制这个循环</span><span class="hint">Human-in-the-loop</span></div>
          <div class="card-b">${humanPanel(l)}</div>
        </div>
      </div>
    </div>
    ${summaryHTML(l.events)}`;
}

function select(i){ CUR=i; renderRail(); renderMain(); window.scrollTo(0,0); }

// 重放：把 tick 卡先藏起来，再一圈圈淡入 —— 让人看见循环“在跑”
function showAll(){ document.querySelectorAll('#traceBody .tickcard').forEach(c=>{ c.style.display=''; c.style.opacity='1'; }); }
function replay(){
  const cards=[...document.querySelectorAll('#traceBody .tickcard')];
  cards.forEach(c=>{ c.style.opacity='0'; c.style.display='none'; });
  let i=0;
  const step=()=>{
    if(i>=cards.length) return;
    const c=cards[i++]; c.style.display='';
    requestAnimationFrame(()=>{ c.style.transition='opacity .35s ease'; c.style.opacity='1'; });
    setTimeout(step,700);
  };
  step();
}
// 人工裁决例外队列 —— 点一下，这一件就被人处理掉了（人控制循环）
function resolveExc(btn,verdict){
  const item=btn.closest('.eqitem'); if(!item) return;
  item.classList.add('done');
  const box=item.querySelector('.btns');
  if(box) box.innerHTML=`<span class="resolved">已${verdict}（人工）</span>`;
}
// ③ 定时式：人工复核大额
function review(btn,verdict){
  verdict=verdict||'复核通过';
  const item=btn.closest('.eqitem'); if(!item) return;
  item.classList.add('done');
  const box=item.querySelector('.btns');
  if(box) box.innerHTML=`<span class="resolved">已${verdict}（人工）</span>`;
}

// ① 对话式：你发一条 → 清单当场裁决。逻辑与 loops/loop1_dialog.py 的
//    mock_reply + acceptance_check 一一对应（同一套规则，看得见地跑）。
function dialogDecide(text){
  const refund=['退款','退货','投诉','索赔','差评','骗','垃圾','态度'];
  const hi = refund.some(w=>text.includes(w));
  const m = text.match(/(订单|order)\s*[#:：]?\s*([A-Za-z0-9]+)/i);
  const cites = !!m;
  const conf = hi?0.45:(cites?0.9:0.72);
  const draft = cites
    ? `您好，订单 ${m[2]} 的信息已为您查到，本店可正常为您处理。`
    : `您好，本店营业时间 9:00–22:00，很高兴为您服务。`;
  if(!CTRL.dialog){   // 控制点关：一律放行（裸奔），高风险也自动发
    return {draft,conf,cites,hi,pass:true,reason:'⚠ 控制点已关：一律放行（裸奔）'};
  }
  let pass=true, reason='';
  if(hi){ pass=false; reason='命中高风险意图（退款/投诉/索赔）→ 强制转人工'; }
  else if(conf<0.6){ pass=false; reason=`置信度 ${conf} < 0.6 → 不自答`; }
  else { reason=`置信度 ${conf}，无高风险信号 → 可自动发出`; }
  return {draft,conf,cites,hi,pass,reason};
}
function tryDialog(){
  const inp=document.getElementById('dlgInput'); const t=(inp.value||'').trim();
  if(!t) return;
  const r=dialogDecide(t);
  const verdict = r.pass
    ? `<div class="verdict pass"><span class="ic">✔</span><span>放行 · ${r.reason}</span></div>
       <div class="draftline">自动回复：${r.draft}</div>`
    : `<div class="verdict esc"><span class="ic">⇢</span><span>转人工 · ${r.reason}</span></div>
       <div class="draftline dim">草稿存箱，人工席接手（这一条你没让它自答）</div>`;
  document.getElementById('dlgOut').innerHTML =
    `<div class="tickcard"><div class="tick-h"><span class="rnd" style="background:var(--accent)">你发的</span>
     <span class="note">${t.replace(/</g,'&lt;')}</span></div>
     <div class="row"><span class="lab">信号</span><span class="val">conf=${r.conf} 引用订单=${r.cites} 高风险=${r.hi}</span></div>
     ${verdict}</div>`;
  inp.value='';
}

// ② 目标式：改预算看结局。与 loop2 一致：每轮 0.25，需 3 轮(=0.75)达标。
function tryGoal(budget,btn){
  document.querySelectorAll('.pbtn').forEach(b=>b.classList.remove('on'));
  if(btn) btn.classList.add('on');
  const out=document.getElementById('goalOut');
  if(!CTRL.goal){   // 控制点关：不跑 verifier，信模型自述 → 第1轮就收工
    out.innerHTML=`<div class="verdict fail"><span class="ic">⚠</span>
      <span>控制点已关：模型第 1 轮就说「完成了」，被采信 → 提前收工（实际只凑齐 1/3，未达标）</span></div>`;
    return;
  }
  const perRound=0.25, needRounds=3;
  const affordable=Math.floor(budget/perRound + 1e-9);
  const pass = affordable>=needRounds;
  if(pass){
    out.innerHTML=`<div class="verdict pass"><span class="ic">✔</span>
      <span>预算 ${budget}：跑满 3 轮，verifier 全绿 → 达标退出（花 0.75）</span></div>`;
  }else{
    out.innerHTML=`<div class="verdict fail"><span class="ic">✘</span>
      <span>预算 ${budget}：跑到第 ${affordable} 轮就超预算 → 安全止损，未达标（没无限烧）</span></div>`;
  }
}

fetch('data.json').then(r=>r.json()).then(d=>{ DATA=d; renderRail(); renderMain(); })
  .catch(e=>{ document.getElementById('main').innerHTML =
    '<div style="padding:40px;color:#b91c1c;font-size:15px">读不到 data.json。<br><br>请用 <b>bash web/serve.sh</b> 启动，再打开它给出的网址；<br>不要直接双击 index.html（file:// 下浏览器会拦掉数据请求）。</div>'; });
