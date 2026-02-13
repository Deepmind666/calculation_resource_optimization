# 璁＄畻璧勬簮鍔ㄦ€佽皟搴︿笌闃茬垎淇濇姢鏋舵瀯锛堜富绾挎枃妗ｏ級

鏇存柊鏃堕棿锛?026-02-11锛圲TC+08:00锛?
## 1. 椤圭洰鐩爣
鏈」鐩潰鍚戞湰鍦扮數鑴?鏈湴鏈嶅姟鍣紝瑙ｅ喅浠ヤ笅闂锛?1. 浠诲姟骞跺彂杩愯鏃?CPU/GPU/鍐呭瓨瀹规槗鎵撴弧銆?2. 浠诲姟鎻愪氦鏃犺妭鍒跺鑷村唴瀛樷€滅垎鐐糕€濓紝绯荤粺鍗℃鐢氳嚦閲嶅惎銆?3. 缂哄皯缁熶竴璋冨害锛屼换鍔′紭鍏堢骇娣蜂贡锛屽叧閿换鍔¤浣庝环鍊间换鍔℃姠鍗犺祫婧愩€?
鏍稿績鐩爣锛?1. 瀹炴椂鐩戞帶璧勬簮锛圕PU銆佸唴瀛樸€丟PU锛夈€?2. 鎸夎祫婧愮姸鎬佸姩鎬佽皟搴︿换鍔¤繘绋嬶紙鎺ョ撼銆佹帓闃熴€侀檺娴併€佹殏鍋?缁堟锛夈€?3. 鍐呭瓨楂樻按浣嶈Е鍙戜繚鎶わ紝浼樺厛淇濊瘉绯荤粺绋冲畾銆?4. 杈撳嚭鍙璁℃棩蹇楋紝渚夸簬澶嶇洏鍜岃皟浼樸€?
---

## 2. 绯荤粺鎬讳綋鏋舵瀯

```mermaid
flowchart LR
    A[浠诲姟鎻愪氦鍏ュ彛] --> B[浠诲姟闃熷垪/浼樺厛绾ч槦鍒梋
    B --> C[鍔ㄦ€佽皟搴﹀櫒 Scheduler]
    C --> D[杩涚▼鎵ц鍣?Executor]
    D --> E[杩愯浠诲姟闆?Running Set]

    F[璧勬簮鐩戞帶鍣?Monitor] --> C
    C --> G[瀹夊叏瀹堟姢鍣?Safety Guard]
    G --> C
    C --> H[浜嬩欢鏃ュ織涓庢寚鏍?Metrics]
```

妯″潡鑱岃矗锛?1. `Monitor`锛氬懆鏈熼噰鏍?CPU/鍐呭瓨/GPU銆?2. `Scheduler`锛氬熀浜庡疄鏃惰祫婧愮姸鎬佸喅瀹氬惎鍔?闃绘柇/閲嶆帓浠诲姟銆?3. `Safety Guard`锛氬湪楂樻按浣嶆垨绱ф€ョ姸鎬佷笅鎵ц淇濇姢鍔ㄤ綔锛堥檷骞跺彂銆佹嫆缁濇柊浠诲姟銆佺粓姝綆浼樺厛绾т换鍔★級銆?4. `Executor`锛氬彧璐熻矗鎵ц琚皟搴﹀櫒鏀捐鐨勪换鍔°€?5. `Metrics`锛氳褰曟瘡娆″喅绛栧拰鐘舵€佸彉鍖栵紝鐢ㄤ簬璇勪及绋冲畾鎬с€?
---

## 3. 璧勬簮鐘舵€佸垎绾?
瀹氫箟涓夋。鐘舵€侊細
1. `NORMAL`锛氳祫婧愬仴搴凤紝鍙寜鏈€澶у苟鍙戞墽琛屻€?2. `HIGH`锛氭帴杩戜笂闄愶紝闄嶄綆骞跺彂骞堕檺鍒朵綆浼樺厛绾т换鍔°€?3. `EMERGENCY`锛氭帴杩戝け绋筹紝鍋滄鏂颁换鍔″苟瑙﹀彂涓诲姩鍥炴敹銆?
涓洪伩鍏嶆ā寮忔姈鍔紝閲囩敤涓ょ绋虫€佹満鍒讹細
1. 璧勬簮骞虫粦锛氬 CPU/鍐呭瓨绛夋寚鏍囧仛鎸囨暟婊戝姩骞冲潎锛圗MA锛夈€?2. 婊炲洖涓庡喎鍗达細浠?`EMERGENCY` 鍥炶惤鏃朵繚鐣欒嫢骞插喎鍗?tick锛岄槻姝㈢灛鏃舵尝鍔ㄥ鑷磋鏀捐銆?
寤鸿闃堝€硷紙鍙厤缃級锛?1. `memory_high_pct = 85`
2. `memory_emergency_pct = 92`
3. `cpu_high_pct = 80`
4. `cpu_hard_pct = 95`
5. `gpu_memory_high_pct = 85`
6. `gpu_memory_emergency_pct = 95`

---

## 4. 璋冨害绛栫暐

### 4.1 浠诲姟妯″瀷
姣忎釜浠诲姟鑷冲皯鍖呭惈锛?1. `priority`锛堟暟鍊艰秺灏忎紭鍏堢骇瓒婇珮锛?2. `estimated_mem_mb`
3. `estimated_cpu_pct`
4. `estimated_gpu_mem_mb`
5. `profile_key`锛堣祫婧愮敾鍍忛敭锛岀敤浜庝及绠楄嚜鏍″噯锛?6. `preemptible`锛堟槸鍚﹀厑璁歌鎶㈠崰缁堟锛?
### 4.2 鎺ョ撼绛栫暐锛圓dmission Control锛?浠诲姟鍦ㄥ惎鍔ㄥ墠蹇呴』杩囦笁閬撴鏌ワ細
1. 棰勬祴鍐呭瓨鍗犵敤鏄惁瓒呰繃绱ф€ラ槇鍊笺€?2. 棰勬祴 CPU 璐熻浇鏄惁瓒呰繃纭笂闄愩€?3. 鑻ュ惎鐢?GPU 淇濇姢锛岄娴嬫樉瀛樺崰鐢ㄦ槸鍚﹁秴杩囬槇鍊笺€?
鑻ヤ换涓€妫€鏌ュけ璐ワ細
1. 闃绘柇鍚姩锛?2. 淇濈暀鍦ㄩ槦鍒椾腑绛夊緟锛?3. 璁板綍闃绘柇鍘熷洜銆?
涓洪伩鍏嶁€滃悓涓€ tick 鍚姩杩囧浠诲姟鈥濆鑷撮娴嬪け鐪燂紝鎺ョ撼鏃堕噰鐢ㄧ疮璁￠绠楋細
1. 姣忔斁琛屼竴涓换鍔★紝绔嬪嵆鎶婂叾浼扮畻璧勬簮璁″叆鏈?tick 鐨勯娴嬭礋杞斤紱
2. 鍚庣画浠诲姟鍦ㄢ€滃凡璁″垝璐熻浇鈥濆熀纭€涓婄户缁垽鏂€?
姝ゅ鏀寔浼扮畻鑷牎鍑嗭紙R15锛夛細
1. 鐪熷疄杩涚▼杩愯鏃堕噰鏍峰嘲鍊?RSS 鍜屽綊涓€鍖?CPU锛?2. 鑻ョ幆澧冨彲鐢?`nvidia-smi`锛屽悓姝ラ噰鏍疯繘绋嬬骇宄板€?GPU 鏄惧瓨锛?3. 鎸?`profile_key` 鏇存柊 EMA 鐢诲儚锛?4. 鍚庣画鍚岀敾鍍忎换鍔″湪鎻愪氦鏃惰嚜鍔ㄦ彁楂樹及绠楀€硷紙鍐呭瓨/CPU/GPU锛屽畨鍏ㄧ郴鏁版斁澶э級銆?
### 4.3 鍔ㄦ€佸苟鍙戠瓥鐣?1. `NORMAL`锛氬苟鍙?= `max_workers`
2. `HIGH`锛氬苟鍙?= `max(max_workers//2, min_workers)`
3. `EMERGENCY`锛氬苟鍙?= 0锛堝彧鍏佽鍥炴敹锛屼笉鍏佽鏂板惎鍔級

### 4.4 闃茬垎鍥炴敹绛栫暐
褰撹繘鍏?`EMERGENCY`锛?1. 鍏堢粓姝綆浼樺厛绾т笖 `preemptible=true` 鐨勪换鍔★紱
2. 姣忚疆鍥炴敹鍥哄畾鏁伴噺浠诲姟锛堝彲閰嶇疆锛夛紱
3. 鎭㈠鍒?`HIGH` 鎴?`NORMAL` 鍚庡啀閫愭鎭㈠鎺ョ撼銆?
---

## 5. 闃叉鈥滃唴瀛樼垎鐐?閲嶅惎鈥濈殑瀹炵幇閫昏緫

鏈」鐩噰鐢ㄢ€滄彁鍓嶉樆鏂?+ 绱ф€ュ洖鏀?+ 璧勬簮棰勭暀鈥濅笁灞備繚鎶わ細
1. **鎻愬墠闃绘柇**锛氬惎鍔ㄥ墠鍋氶娴嬶紝涓嶈浠诲姟鎶婂唴瀛樻帹鍒板嵄闄╁尯銆?2. **绱ф€ュ洖鏀?*锛氬凡鍒板嵄闄╁尯鏃讹紝涓诲姩缁堟浣庝紭鍏堢骇浠诲姟锛屽揩閫熸琛€銆?3. **璧勬簮棰勭暀**锛氫繚鐣?`reserve_memory_mb` 缁欑郴缁熷拰鍏抽敭杩涚▼锛岄伩鍏?OS 琚尋鐖嗐€?
璇存槑锛?1. 杞欢灞傞潰鍙互鏄捐憲闄嶄綆椋庨櫓锛?2. 浣嗘棤娉曟壙璇?100% 涓嶉噸鍚紙渚嬪椹卞姩寮傚父銆佺‖浠舵晠闅溿€佸閮ㄨ繘绋嬫姠鍗狅級銆?
---

## 6. 鏁版嵁涓庢棩蹇?
姣忎釜璋冨害鍛ㄦ湡杈撳嚭锛?1. 璧勬簮蹇収锛圕PU/鍐呭瓨/GPU锛?2. 褰撳墠妯″紡锛圢ORMAL/HIGH/EMERGENCY锛?3. 鍚姩浠诲姟鍒楄〃
4. 闃绘柇浠诲姟鍒楄〃鍙婂師鍥?5. 鍥炴敹浠诲姟鍒楄〃鍙婂師鍥?6. 杩愯涓换鍔℃暟銆佹帓闃熶换鍔℃暟

鍏抽敭鎸囨爣锛?1. `admission_blocked_total`
2. `preempted_total`
3. `emergency_ticks`
4. `completed_total`
5. `scheduler_tick_ms`

---

## 7. 鍏抽敭娴佺▼锛圱ick锛?姣忔璋冨害寰幆鍋?6 浠朵簨锛?1. 閲囨牱璧勬簮銆?2. 鍒锋柊杩愯浠诲姟鐘舵€侊紙鍥炴敹宸插畬鎴愪换鍔★級銆?3. 鍒ゅ畾褰撳墠璧勬簮妯″紡銆?4. 濡備负绱ф€ユā寮忥紝瑙﹀彂鎶㈠崰鍥炴敹銆?5. 鎸夌洰鏍囧苟鍙戝皾璇曟帴绾抽槦鍒椾换鍔°€?6. 璁板綍浜嬩欢涓庢寚鏍囥€?
---

## 8. 宸ョ▼瀹炵幇钀界偣锛堝搴斿綋鍓嶄粨搴擄級
1. 鏍稿績瀹炵幇锛歚prototype/resource_scheduler.py`
2. 婕旂ず鍏ュ彛锛歚prototype/main.py`
3. 鍘嬫祴/瀹為獙锛歚prototype/run_experiments.py`
4. 鍗曞厓娴嬭瘯锛歚prototype/tests/test_resource_scheduler.py`
5. 閰嶇疆鏍蜂緥锛歚spec/scheduler_config.example.json`
6. 閰嶇疆鏍￠獙锛歚qa/validate_scheduler_config.py`

---

## 9. 杩唬璁″垝

Phase 1锛堝凡瀹炵幇鐩爣锛夛細
1. 鍩虹璋冨害鍣?2. 璧勬簮鐘舵€佸垎绾?3. 闃茬垎鍥炴敹
4. 鍗曞厓娴嬭瘯涓庡疄楠屾寚鏍囪緭鍑?
Phase 2锛堜笅涓€闃舵锛夛細
1. 鏇寸簿缁嗙殑浠诲姟璧勬簮棰勬祴锛堝姞鍏ュ惎鍔ㄥ悗鍓?N 绉掑嘲鍊煎垎娈靛缓妯′笌鍒嗕綅鏁颁繚鎶わ級
2. 浠诲姟鏆傚仠/鎭㈠锛堜笉浠呮槸缁堟锛?3. 澶氶槦鍒楃瓥鐣ワ紙瀹炴椂浠诲姟銆佹壒澶勭悊浠诲姟鍒嗙锛?4. 鍙鍖栫湅鏉夸笌鍛婅閫氱煡

---

## 10. 鐪熸満鍩虹嚎瀹為獙鏈夋晥鎬х害鏉燂紙R19锛?涓洪伩鍏嶁€滃弬鏁拌繃杞诲鑷村疄楠屾棤鏁堚€濓紝`run_advanced_research.py --run-real-baseline` 閲囩敤浠ヤ笅璐ㄩ噺闂ㄦ锛?1. 鍙娴嬫€ч棬妲涳細闇€瑕佸彲閲囬泦涓绘満鍐呭瓨宄板€硷紙`psutil` 鍙敤锛夛紱鑻ヤ笉鍙敤鍒欏簲鏄惧紡鏍囨敞缁撴灉涓嶅叿澶囧嘲鍊煎彲姣旀€с€?2. 璐熻浇闂ㄦ锛氱湡瀹炰换鍔¤礋杞藉弬鏁颁笉鑳介暱鏈熷仠鐣欏湪浣庡帇鍖猴紝鑷冲皯搴旀弧瓒斥€滃彲瑙﹀彂 HIGH 鎴?EMERGENCY 鐨勫彲鑳芥€р€濄€?3. 鏃堕暱闂ㄦ锛氬崟浠诲姟鎵ц鏃堕暱涓嶈兘杩囩煭锛岄渶淇濊瘉璋冨害鍣ㄦ湁瓒冲 tick 瑙傚療 admission/block/preempt 閾捐矾銆?4. 鏈夋晥鎬ч棬妲涳細杈撳嚭涓繀椤诲彲鏍搁獙 `emergency_ticks`銆乣preempted_total`銆乣blocked_event_total`銆乣scheduler_timeout_hit`銆?5. 瀹夊叏闂ㄦ锛氬帇鍔涘弬鏁板簲渚濇嵁涓绘満鎬诲唴瀛樺姩鎬佹敹鏁涳紝閬垮厤涓轰簡瑙﹀彂浜嬩欢鑰屽埗閫犱笉鍙帶 OOM 椋庨櫓銆?6. 鏁版嵁璐ㄩ噺闂ㄦ锛欸PU 宄板€肩櫨鍒嗘瘮闇€閫氳繃閲囨牱鍋ュ．鎬х害鏉燂紙闈炴硶/寮傚父鍊艰繃婊や笌涓婇檺绾︽潫锛夛紝闃叉璇佹嵁琚紓甯搁噰鏍锋薄鏌撱€?
---

## 11. 鐩爣浜嬩欢椹卞姩鐪熸満鍩虹嚎锛圧20锛?涓烘彁鍗囩湡鏈鸿瘉鎹川閲忥紝寮曞叆鈥滅洰鏍囦簨浠堕┍鍔ㄢ€濈殑瀹為獙鎺у埗娴佺▼锛?1. 鍒濆鍙傛暟鎸?R19 瑙勫垝鍣ㄦ敹鏁涘埌鍙墽琛屽尯闂达紱
2. 鎵ц涓€杞湡鏈哄熀绾垮悗妫€鏌ュ叧閿簨浠讹細
   - 鏄惁鍑虹幇 `emergency_ticks > 0` 鎴?`preempted_total > 0`锛?   - 鏄惁鍑虹幇 `low_signal_dynamic=1`锛?3. 鑻ヤ俊鍙蜂笉瓒筹紝鍒欏湪瀹夊叏棰勭畻鍐呰嚜鍔ㄥ姞鍘嬮噸璺戯紙澧炲ぇ `base_mem_mb`銆佹媺闀?`duration_sec`銆佹彁楂?`task_count`锛夛紱
4. 鍚屾椂鎸夊皾璇曡疆娆℃敹绱ц皟搴﹂槇鍊硷紙memory high/emergency銆乸reempt count锛夛紝鎻愰珮 emergency/preempt 瑙﹀彂鍙娴嬫€э紱
5. 杈惧埌浜嬩欢鐩爣鎴栬揪鍒版渶澶у皾璇曟鏁板嵆鍋滄锛?6. 璁板綍姣忔灏濊瘯鍙傛暟涓庣粨鏋滐紝鏀寔璇勫鍥炴函鈥滀负浠€涔堣繖涓€杞湁鏁?鏃犳晥鈥濄€?
---

## 12. 鍙岀洰鏍囪瘉鎹ā寮忥紙R22锛?涓哄洖搴斺€滀粎璇佹槑瀹夊叏銆佹湭璇佹槑鍚炲悙鈥濈殑璇勫鎰忚锛岀湡鏈哄熀绾垮鍔犲彲閫夊弻鐩爣妯″紡锛?1. 瀹夊叏鐩爣锛氬繀椤诲嚭鐜?`emergency_ticks > 0` 鎴?`preempted_total > 0`锛?2. 鍚炲悙鐩爣锛氬悓涓€鍔ㄦ€侀樁娈靛繀椤绘弧瓒?`completed > 0`锛堝彲閰嶇疆鏈€灏忓畬鎴愭暟锛夛紱
3. 鑻ヤ粎婊¤冻瀹夊叏鐩爣浣嗗悶鍚愪笉瓒筹紝鍒欑户缁噸璇曞苟寤堕暱璋冨害绐楀彛锛?4. 姣忚疆灏濊瘯璁板綍鈥滈噸璇曞師鍥犫€濓紙濡?`missing_emergency_signal`銆乣insufficient_completion`锛夛紝淇濊瘉鍙В閲婃€с€?
## 13. Adaptive Dual-Objective Retry (R23)
R22 adds dual objectives (safety + throughput). R23 adds reason-aware adaptation to improve convergence on real hosts:
1. Keep 'threshold_bias' as per-attempt state for dynamic scheduler thresholds.
2. If retry reason is 'insufficient_completion', relax thresholds ('threshold_bias += 8') and extend scheduler wall budget; avoid extra pressure escalation in this branch.
3. If retry reason is 'low_signal_dynamic' or 'missing_emergency_signal', tighten thresholds ('threshold_bias -= 4') and escalate workload pressure for better emergency/preempt observability.
4. Every attempt must record applied thresholds, 'threshold_bias', and 'retry_reason' for traceability.
5. Safety semantics remain unchanged: new admissions stay blocked in emergency mode, and preemption remains enabled.