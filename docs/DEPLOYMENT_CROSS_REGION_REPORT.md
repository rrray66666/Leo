# Deploying a CRM System on a China Domestic Server with Cross-Country Access: Risks & Considerations

**Scope**: Risk analysis and deployment guidance for a CRM system (Vue3 frontend + FastAPI backend + MySQL + Redis + MinIO, deployed with Docker Compose) hosted on a mainland-China (domestic) server, with users accessing from inside and outside China.

**Date**: 2026-08-05
**Status**: Research report based on current (2026) public sources; not legal advice. Verify all compliance statements with qualified counsel before launch.

---

## 1. Domain & Compliance Risks (China-Specific)

### 1.1 ICP Filing (ICP备案) — Mandatory Before Going Live

- Under the *Administrative Measures on Internet Information Services* and the *Measures on the Administration of Filings for Non-operating Internet Information Services*, **every website whose domain resolves to a mainland-China server must complete ICP filing (备案) with the MIIT**. A domain without filing is not allowed to go online, and a filed domain must resolve to a filed IP address [1].
- Practical consequence for CDN: choosing the "Mainland China" or "Global" acceleration region on Alibaba Cloud / Tencent Cloud CDN **requires the domain to be ICP-filed**. An unfiled domain can only use the "Global (excluding Mainland China)" region (overseas nodes only), which means mainland users get poor performance [2][3].
- **Foreign companies cannot apply directly**: ICP filing requires a Chinese legal entity (WFOE, Joint Venture) or a sponsoring Chinese partner. Filing itself is free and takes ~20–30 working days; incorporating first extends the end-to-end timeline to 3–6 months and typically US$3,000–15,000 in total project cost [4].
- **ICP Filing vs ICP Commercial License**: a pure brochure/informational site only needs the filing (备案). If the site sells, lists prices, accepts paid sign-ups, or runs paid advertising, MIIT may classify it as commercial and require the **ICP License (ICP许可证)**. A CRM used as a paid SaaS channel is at risk of being treated as commercial — confirm this early [4].
- Obligations after approval: display the ICP number in the footer of every page, and complete **public security (公安) filing** at the local PSB **within 30 days of the site going live** [1].
- Real-name verification of the domain and of the hosting account is required before filing can proceed [1].

### 1.2 Cross-Border Data Transfer (PIPL 个人信息保护法)

The PIPL (effective 2021-11-01) applies to any organization processing personal information (PI) of individuals in China — including foreign organizations serving Chinese individuals. It also has extraterritorial effect [5].

- **Three lawful routes** for transferring PI out of mainland China (PIPL Art. 38): (a) CAC security assessment, (b) standard contract (SCC) filing with the provincial CAC, or (c) PI protection certification (the certification measures took effect 2026-01-01) [5][6][7].
- **Threshold-triggered routes** (per the *Provisions on Promoting and Regulating Cross-Border Data Flows*, effective 2024-03-22, and the CAC notice of 2025-03-21):
  - **Mandatory CAC security assessment**: CIIO operators; non-CIIO transferring "important data"; or non-CIIO transferring ≥ 1 million individuals' PI cumulatively, or ≥ 100,000 individuals' PI (or ≥ 10,000 individuals' **sensitive** PI) since Jan 1 of the current year [7][8].
  - **Standard contract or certification**: non-CIIO transferring 100,000–1,000,000 individuals' PI (or < 10,000 sensitive) per year [7][8].
  - **Exempt** (no route required, base PIPL obligations still apply): non-CIIO transferring < 100,000 individuals' PI per year [7][8].
- **What counts as "outbound transfer" matters**: providing overseas users (or overseas staff) access to PI stored in mainland China — e.g., a CRM accessed from abroad — is generally treated as providing PI to parties outside China and can trigger the rules. Chinese enterprises that sync HR/CRM data from the mainland head office to overseas entities routinely discover they owe outbound-compliance obligations [8].
- **Practical read for this CRM**: it stores customer/contact PI. If the volume of data subjects is small (< 100K) and no "important data" is involved, the three routes are likely not triggered — but a privacy policy, consent for contact persons, purpose limitation and data-minimization still apply. If the company later replicates CRM data to an overseas DB/replica or opens the system to overseas staff at scale, re-evaluate thresholds each year [5][7][8].

### 1.3 Data Residency Requirements

- Under the Cybersecurity Law (CSL), Data Security Law (DSL) and PIPL, **PI and "important data" collected and generated in China must be stored in China by default**; outbound transfer is only allowed after satisfying the assessment/contract/certification conditions above [1][8].
- The *Regulations on Network Data Security Administration* (State Council Order No. 790, effective 2025-01-01) further require classified-and-graded data protection, encryption, backup, access control, incident reporting (24h for serious incidents), and contract obligations with data recipients [9].
- **Design implication**: keep the single MySQL primary (and backups) inside mainland China. Do not add an overseas DB replica holding CRM PI unless the outbound routes have been assessed. Serving an overseas user's browser request over HTTPS does **not** itself require data replication — the data can remain in China.

### 1.4 Security-Level Protection (等保 / MLPS 2.0)

- MLPS 2.0 (baseline standard **GB/T 22239-2019**, effective 2019-12-01) is mandatory under CSL Art. 21 for networks/information systems operating in China — including cloud deployments [10][11].
- **Levels**: Level 1 (self-protection, no filing), Level 2 (filing with local PSB + assessment every 2 years — typical for SME websites, ordinary OA, systems without massive personal data), Level 3 (annual assessment; typical for e-commerce, apps, and systems processing ≥ 1M individuals' PI), Level 4/5 (critical infrastructure / state systems) [10][12].
- Registration must occur within 30 days of the protection level being determined (draft rules may shorten this to 10 days for Level 2+) [11].
- **Practical read for this CRM**: a small/medium CRM serving a company's sales team is most likely **Level 2** (file with the local PSB, implement baseline controls: identity authentication, access control, security audit, backups, encryption, intrusion prevention). If the CRM is offered as a public SaaS holding large volumes of customer PI, plan for Level 3 [10][12].
- Note that cloud providers (Alibaba Cloud, Tencent Cloud, etc.) hold MLPS 2.0 Level 3 certifications for their platforms; this covers the platform layer, **not your application** — your application layer still needs its own classification, filing and controls [13].

---

## 2. Access Speed & Latency Issues

### 2.1 Why Overseas Users Are Slow

- **Physics**: one-way theoretical latency China–US is ~100 ms, but real routing adds hops, pushing actual RTT to **300–500 ms**. Peak-hour utilization of China's international export bandwidth often exceeds 80%, with **packet loss of 15–20%** — under which TCP throughput collapses and large transfers repeatedly retransmit [14].
- **Domestic CDN only partially helps**: a CDN (e.g., Alibaba DCDN) caches static content at edge nodes; overseas users hitting cached static assets get fast responses. But **dynamic requests (API, login, search, HTML) always back-to-origin**, crossing the international gateway back into mainland China — these stay slow. Low cache hit rates, missing `Cache-Control`, and repeated cross-border TLS handshakes all add latency [15][2].
- **Why "the site is slow even with a CDN" is a misconfiguration problem in many cases**: wrong acceleration region (only mainland selected), no differentiation of cacheable HTML vs non-cacheable APIs, HTTPS handshake issues (missing HTTP/2, OCSP stapling), and geo-routing that sends German users to Singapore nodes [16].

### 2.2 Solution Options

| Option | What it does | Best for | Caveats |
|---|---|---|---|
| **Domestic CDN with "Global" acceleration region** (Alibaba/Tencent/EdgeOne) | Serves both mainland and overseas users from nearby edge nodes; caches static assets | Static assets (JS/CSS/images/uploaded docs) | Requires ICP filing for Global/Mainland region; dynamic API still back-to-origin [3][17] |
| **International CDN (Cloudflare free tier, AWS CloudFront, Akamai)** | 200+ city global edge network; no filing needed for overseas-only regions | Overseas users | **Mainland access via Cloudflare is unstable** (traffic routed to HK/Tokyo/Singapore, highly ISP-dependent; some mainland ISPs intermittently fail) [17][18] |
| **Full-site / dynamic acceleration (DCDN / ESA / EdgeOne)** | Edge caching + protocol optimization (HTTP/2/3, compression) for dynamic content | APIs where TTFB matters | Cannot remove the cross-border back-to-origin hop entirely when origin is in mainland [15][19] |
| **Cross-border dedicated lines / GA** (e.g., Volcengine GA, IPLC, SD-WAN) | Optimized backbone with compliant cross-border circuits (mainland–HK 2–3 ms, Shanghai–Tokyo 23–25 ms, Shanghai–Seoul 21–22 ms, Beijing–Frankfurt 113–117 ms) | Real-time/high-QoS dynamic traffic | Requires **cross-border compliance review** with a licensed carrier (only 3 mainland carriers hold cross-border operation licenses); cost is the highest [20] |
| **Overseas origin (HK/Singapore) + GSLB/GeoDNS split** | Route mainland users to mainland origin, overseas users to HK/Singapore origin | Sustained significant overseas usage | Data replication/sync complexity and outbound-data compliance; see §3.4 [15][21][22] |

Diagnosis tips: use `mtr`/TCP traceroute from overseas probes; check CDN response headers (`x-cache: HIT` vs `MISS`) to confirm whether the request truly crossed into mainland [23][15].

---

## 3. Cross-Region Architecture Recommendations

### 3.1 CDN for Static Assets (Recommended, Do First)

- Move to a dedicated asset subdomain (e.g., `assets.example.com`) for the built Vue3 bundles, and serve MinIO documents/images through CDN (MinIO presigned URLs or a CDN-hosted public bucket with signed back-to-origin).
- Select acceleration region **"Global"** on Alibaba/Tencent CDN so mainland and overseas users both hit nearby nodes (requires the domain to be ICP-filed) [3][17].
- Configure long cache lifetimes for hashed static assets (the project's nginx already uses `Cache-Control: public, immutable` for `/assets/` — mirror this at the CDN layer), `gzip`/Brotli, HTTP/2, and proper `Access-Control-Allow-Origin` headers so the SPA can call the API cross-origin (CDN + backend both need CORS configured) [24].
- `Dockerfile`/`nginx.conf` note: the current nginx proxies `/api/` to the backend on the same host. If you later put the CDN in front of the whole domain, configure CDN rules so **`/api/*` is never cached** (or bypasses to origin) while static paths are cached aggressively [15].

### 3.2 API Latency Mitigation

- The FastAPI backend is dynamic — CDN caching does not help. For a small CRM whose overseas usage is occasional, **accept the 300–500 ms cross-border RTT**; keep the API on the mainland primary and focus on making each request cheap (compact JSON, gzip, keep-alive, Redis caching for hot queries).
- If overseas API speed becomes a requirement, in order of cost: (1) full-site acceleration product (DCDN/ESA/EdgeOne) to optimize the cross-border path and TLS, (2) Global Accelerator-style TCP optimization, (3) an HK/Singapore read-only entry (see §3.4). Each next step adds cost and complexity [15][20].

### 3.3 Global Load Balancing (GSLB / GeoDNS)

- For split routing, the mainstream approach is **DNS-based GSLB**: mainland users resolve to the mainland origin/CDN; overseas users resolve to Cloudflare (via **Cloudflare SaaS / Custom Hostnames**) or an overseas origin. Keep authoritative DNS at Alibaba Cloud DNS and use **split-line (分线路) rules** — this is a well-tested pattern for "overseas primary, mainland fallback" and vice versa [21].
- Caveats: DNS-based routing sees the LocalDNS IP, not the user's real IP (public DNS like 8.8.8.8 degrades accuracy); DNS TTL caching delays failover by minutes. Anycast (e.g., Cloudflare/GA) gives request-level precision but is more complex [25].
- The pattern that fits this project: **mainland users → domestic CDN / mainland origin; overseas users → Cloudflare edge → back-to-origin to the mainland server** (or an HK entry). This avoids making overseas users traverse the GFW gateway directly and gives them TLS/HTTP2/3 termination at the edge [21].

### 3.4 Database Sync / Read-Replica Considerations for Cross-Region

- **Avoid multi-master or dual-write at this stage.** Cross-region DB synchronization brings dual-write complexity, sync latency, and data-conflict problems that are disproportionate for a small CRM [22].
- Reasonable future options:
  - **Read replica** (e.g., MySQL replica in an HK region, or a regional cloud DB with read-only endpoint) serving overseas read-heavy workloads — only if measurable overseas usage justifies it; keep writes on the mainland primary.
  - **MinIO replication** (`mc mirror`) to an HK bucket if large document downloads for overseas users matter — but note this copies documents out of mainland (check the PIPL "important data"/PI classification of the document content).
  - **Important**: any replica that stores PI outside mainland triggers the cross-border rules from §1.2 — a read replica is still an outbound transfer of PI. For a small CRM, the compliance cost usually outweighs the latency benefit; prefer "data stays in mainland, traffic rides an acceleration layer" [1][8].
- Keep Redis with the primary (sessions/caches are ephemeral; JWT auth in this project is stateless so no cross-region session glue is needed).

---

## 4. Security Risks

### 4.1 DDoS Protection

- Mainland cloud providers include basic DDoS mitigation with the platform (e.g., Alibaba Cloud free baseline ~5 Gbps); for a public-facing CRM consider **Anti-DDoS Pro/Premium** with "保底 (committed) + 弹性 (elastic)" billing so you only pay for burst capacity when actually attacked [26][27].
- For the "mainland origin + overseas users" profile, Alibaba **Anti-DDoS Premium (非中国内地) with the security-acceleration line** is the product designed exactly for that scenario (overseas scrubbing nodes + acceleration back into mainland) [27][28].
- **Hide the origin IP**: once a CDN/high-defense proxy fronts the domain, restrict the security group so only the proxy/CDN IPs can reach 80/443; an exposed origin IP bypasses all DDoS/CDN protection [28].
- Practical hardening for this project: currently `docker-compose.yml` publishes MySQL (3306), Redis (6379), and MinIO (9000/9001) on the host. In production bind these to `127.0.0.1` or remove the host port mapping and only expose 80/443 through the nginx container — exposed database/cache/object-store ports are an immediate attack surface.

### 4.2 API Abuse / Brute-Force Protection

- Login brute force on `/api/auth`: implement Redis-based per-IP/per-account rate limiting (the project already uses Redis), lockout after N failures, and CAPTCHA after repeated failures; consider `fail2ban` at the host level.
- WAF layer: Alibaba WAF, Tencent EdgeOne, or Cloudflare WAF for the overseas path; block SQLi/XSS/credential stuffing patterns at the edge.
- Rate limiting on all write endpoints (customers, contracts, tasks) and on the search endpoint; set per-user QPS ceilings.
- Keep `JWT_SECRET` and MinIO credentials in the environment file only (never in images), rotate on rotation schedule, and restrict MinIO bucket policies to the backend service account.

### 4.3 HTTPS / SSL Certificate Requirements

- **No separate "SSL filing" exists**, but the domain must be ICP-filed before mainland hosting/CDN/HTTPS on mainland services; unfiled domains cannot deploy certificates against mainland endpoints either [29][30].
- **International CA certs (Let's Encrypt, DigiCert, GlobalSign, Sectigo)** are valid and widely used on mainland servers; DV certificates are generally acceptable for MLPS assessments. Enforce TLS 1.2+, disable weak cipher suites (SHA-1, RC4), serve full certificate chains, and auto-renew (Let's Encrypt = 90-day certs; certbot auto-renewal) [31].
- **国密 (SM2) certificates**: only needed for government/finance/信创-style MLPS or 密评 (crypto-assessment) scenarios. If required, use a licensed domestic CA (CFCA, WoSign, etc.) and consider a **dual-cert (international + SM2) deployment** so ordinary browsers still work [32][33].
- For the CDN/edge layer: use the CDN's managed certificate (or upload one) and enable HTTP/2 + OCSP stapling — cross-border TLS handshakes are a measurable latency cost, so edge TLS termination helps [16][31].

---

## 5. Recommended Deployment Strategy

**Profile**: small CRM (Vue3 + FastAPI + MySQL + Redis + MinIO, single-host Docker Compose), users mainly in China, occasional overseas access.

### 5.1 Recommended Baseline (do this first)

1. **Mainland server + ICP-filed domain** (requires a Chinese legal entity — start the incorporation/filing process 3–6 months before go-live if the operator is foreign) [4].
2. **Domestic CDN (Alibaba Cloud CDN / Tencent CDN / EdgeOne) with acceleration region = "Global"** in front of the static frontend; the API path bypasses CDN caching and proxies to the mainland origin [3][17].
3. **Single primary data plane in mainland China**: one MySQL primary, Redis cache, MinIO object store — no overseas data replication. This keeps the PIPL/data-residency position simple (§1.2/§1.3) [1][8].
4. **HTTPS everywhere** with an international DV/OV certificate (Let's Encrypt is fine), TLS 1.2+, HTTP/2, gzip/Brotli [31].

### 5.2 If Overseas Users Become Significant (evolution path)

- **Phase 2 — edge-only acceleration, no data move**: add **Cloudflare (free tier) via Cloudflare SaaS Custom Hostnames + DNS split-line** at Alibaba Cloud DNS: mainland line → domestic CDN/origin, overseas line → Cloudflare edge → back-to-origin to the mainland server. This gives overseas users edge TLS/HTTP2/3 and avoids GFW-crossing direct connections, at ~zero CDN cost for the overseas path [21][18].
- **Phase 3 — regional entry**: only if latency is still unacceptable, add an **HK origin/reverse proxy** (HK has no ICP filing, CN2 GIA lines give mainland latency ~30–50 ms and overseas ~150–180 ms) or a Global Accelerator-type product with a compliant cross-border line [20][34][35]. If you add a read replica or document replication for overseas, run the PIPL outbound assessment first (§1.2) [8].
- **Not recommended for this scale**: Cloudflare China Network (Enterprise-only subscription operated with JD Cloud; requires ICP per domain — cost is prohibitive for a small CRM) [18]; multi-region MySQL clusters (complexity/compliance cost outweighs benefit) [22].

### 5.3 Cost Considerations (indicative, 2026)

| Item | Indicative cost | Notes |
|---|---|---|
| ICP filing (MIIT) | Free | But needs a Chinese entity; WFOE path ≈ US$3,000–15,000 all-in [4] |
| Mainland cloud server (4C/8G, ~5Mbps BGP) | ¥200–600/month | Host for Docker Compose stack |
| Domestic CDN (Global region) | Pay-as-you-go traffic (~¥0.2–0.5/GB, higher overseas) | Static assets only; keep API off CDN [3][24] |
| Cloudflare free tier (overseas path) | $0 | 200+ node edge; mainland performance not guaranteed [17][18] |
| DDoS Anti-DDoS basic | Included / ~¥3,000+/month for 30Gbps committed + elastic | Add only when exposed to attack risk [26][28] |
| MLPS Level 2 filing + assessment | ~¥20,000–50,000 depending on vendor | Filing is mandatory; assessment typically every 2 years [10][12] |
| HK origin server (if Phase 3) | ~¥100–300/month + cross-border line costs | No ICP needed; PIPL outbound review required for PI [34][35] |

---

## 6. Practical Checklist

**Legal & Compliance**
- [ ] Confirm the operating entity can hold an ICP filing (WFOE/JV/sponsor); start incorporation 3–6 months before launch if needed [4].
- [ ] Register the domain with real-name verification; begin ICP filing (20–30 working days) — do not launch before filing completes [1][4].
- [ ] After launch: display the ICP number in the page footer; complete **public security (公安) filing within 30 days** [1].
- [ ] Determine whether the service is "non-commercial" (filing) or "commercial" (ICP license) — a paid SaaS CRM likely needs the license; confirm with counsel [4].
- [ ] Data inventory: list PI fields in the CRM (customer contacts, users); minimize collection; add a privacy policy and consent/notification for contacts [5][8].
- [ ] Estimate outbound volumes: if < 100K data subjects/year and no important data, the three PIPL outbound routes are not triggered; **do not replicate CRM data to an overseas DB**; if overseas staff/users access the system, track this as potential outbound transfer and re-assess annually [7][8].
- [ ] MLPS: classify the system (expect Level 2 for an internal small CRM; Level 3 if large-scale public SaaS with ≥1M PI); register with the local PSB; schedule the periodic assessment [10][12].

**Network & Performance**
- [ ] Add the domain to a domestic CDN with acceleration region "Global"; create `assets.example.com` for static bundles [3][17].
- [ ] Configure CDN cache rules: long TTL + immutable for hashed assets; **never cache `/api/*`**; enable gzip/Brotli, HTTP/2, TLS 1.2+ [15][16].
- [ ] Configure CORS at both CDN and FastAPI so the SPA can call the API cross-origin [24].
- [ ] (Optional) Set up DNS split-line + Cloudflare SaaS for the overseas path [21].
- [ ] Validate from 5–10 overseas probes with `mtr` and check `x-cache: HIT/MISS`; target <2.5s first load and stable API TTFB [23][15].

**Security**
- [ ] Firewall/security group: expose only 80/443; bind MySQL/Redis/MinIO to the internal Docker network (remove the `3306/6379/9000/9001` host port mappings in `docker-compose.yml`) — see note in §4.1.
- [ ] Login protection: Redis rate limiting, account lockout, optional CAPTCHA; `fail2ban` for SSH [§4.2].
- [ ] WAF at the edge; rate limits on write/search endpoints [§4.2].
- [ ] Enable cloud DDoS basic protection; add Anti-DDoS (保底+弹性) only if exposed; keep the origin IP hidden behind CDN [26][28].
- [ ] TLS: auto-renewing DV certificate (certbot), full chain, TLS 1.2+ only [31].

**Operations**
- [ ] Daily MySQL backups to an in-region (mainland) object store; test restore [9].
- [ ] Uptime/health monitoring from both mainland and overseas vantage points; alert on TTFB and error rates [2].
- [ ] Keep `.env` secrets (DB password, JWT secret, MinIO keys) out of version control and images; rotate regularly [§4.2].

---

## Sources

1. Microsoft Learn — Data sovereignty and China regulations (ICP filing, PSB filing, cross-border transfer FAQ): https://learn.microsoft.com/en-us/azure/china/overview-sovereignty-and-regulations
2. Alibaba Cloud Help — Slow website access after using Alibaba Cloud CDN (acceleration region vs ICP filing): https://help.aliyun.com/en/cdn/user-guide/website-access-speed-is-slow-after-using-alibaba-cloud-cdn-1
3. CSDN — 海外服务器能否接入国内CDN (domestic CDN filing rules, acceleration regions, Cloudflare alternative): https://blog.csdn.net/szshxkj/article/details/160928321
4. MS Advisory — ICP License in China: How Foreign Companies Get Approved in 2026: https://msadvisory.com/icp-license-china/
5. KnowledgeLib — China's PIPL Requirements: scope, cross-border transfers, penalties: https://knowledgelib.io/compliance/privacy/pipl-china/2026
6. Global Law Experts — PIPL Cross-Border Transfer Certification in China (2026): https://globallawexperts.com/pipl-crossborder-transfer-certification-china-2026/
7. CCPIT — 中企出海数据合规：境内规则与目的地监管的双重视角 (data-outbound thresholds per 促跨新规 and 2025 CAC notice): https://www.eccpit.com/news/Y21zcG86MjMxNjQ
8. CSDN — 数据安全指南-合规治理 (PIPL/DSL/GDPR comparison, outbound mechanisms & thresholds): https://blog.csdn.net/hyc010110/article/details/153341526
9. Gov.cn — 网络数据安全管理条例 (State Council Order No. 790, effective 2025-01-01): https://www.gov.cn/gongbao/2024/issue_11646/202410/content_6980863.html
10. CSDN — 等保2.0实施方案 (MLPS 2.0 levels, GB/T 22239-2019, assessment cadence): https://blog.csdn.net/sundehui01/article/details/162695813
11. Protiviti — Multiple-Level Protection Scheme 2.0 compliance procedure (MLPS levels, 30-day registration): https://www.protiviti.com/sites/default/files/2022-09/pov-multiple-level-protection-scheme-cn.pdf
12. AppInChina — What is China's MLPS Filing and Who Needs One (Level 2/3 applicability): https://appinchina.co/what-is-an-mlps-filing-and-who-needs-one/
13. Alibaba Cloud Help — MLPS security hardening for ACK (platform-level MLPS 2.0 Level 3): https://help.aliyun.com/en/ack/ack-managed-and-ack-dedicated/security-and-compliance/ack-reinforcement-based-on-classified-protection
14. 时耕通讯 (Shigeng Telecom) — Optimize access to domestic file servers from overseas (cross-border latency physics, IPLC/SD-WAN): https://www.shigengtelecom.com/1035.html
15. CSDN — 为什么用了阿里云 DCDN 全站加速，国外访问仍然慢 (static vs dynamic, back-to-origin bottleneck, GSLB/GA): https://blog.csdn.net/solocao/article/details/152893578
16. 亿英宝 — Why your site is still slow despite CDN (misconfiguration: geo-routing, HTTPS, cache rules): https://www.eyingbao.net/en/news/wangzhanjianshe_SEO/weishenmenidedulizhanyongleCDNhaishika_3leidianxingpeizhicuowuzhengzaituokuahaiwaiyonghuzhuanhualyu.html
17. 腾讯云开发者 — 海外访问国内节点慢？如何申请海外CDN加速 (Tencent Cloud global CDN, ICP requirement for Global region): https://cloud.tencent.com.cn/developer/information/%E6%B5%B7%E5%A4%96%E8%AE%BF%E9%97%AE%E5%9B%BD%E5%86%85%E8%8A%82%E7%82%B9%E6%85%A2%E7%9A%84%E7%A6%BB%E8%B0%B1%E3%80%82%E5%A6%82%E4%BD%95%E7%94%B3%E8%AF%B7%E6%B5%B7%E5%A4%96CDN%E5%8A%A0%E9%80%9F%E3%80%82
18. HostEase CN — Cloudflare CDN 中国大陆访问加速实战配置指南 (Cloudflare mainland status, China Network = Enterprise + JD Cloud + ICP per domain): https://cn.hostease.com/blog/cdn/cloudflare-cdn-china-acceleration/
19. Alibaba Cloud Help — Website loads slowly after enabling ESA (acceleration region, cache/dynamic diagnostics): https://www.alibabacloud.com/help/en/edge-security-acceleration/esa/support/faq-2-1/
20. 火山引擎 — 海外→国内加速回源：四层加速 + CDN 分发 (compliant cross-border lines, latency table, carrier compliance review): https://www.volcengine.com/docs/6737/1400243
21. CSDN — 海外业务为主场景下，使用 Cloudflare SaaS + DNS 分线路的实践方案 (split-line DNS pattern): https://blog.csdn.net/solocao/article/details/156895127
22. 腾讯云开发者 — 海外部署访问技术探索 (data sync/dual-write complexity for cross-border): https://cloud.tencent.com.cn/developer/information/%E6%B5%B7%E5%A4%96%E8%AE%BF%E9%97%AE%E5%9B%BD%E5%86%85%E8%8A%82%E7%82%B9%E6%85%A2%E7%9A%84%E7%A6%BB%E8%B0%B1%E3%80%82%E5%A6%82%E4%BD%95%E7%94%B3%E8%AF%B7%E6%B5%B7%E5%A4%96CDN%E5%8A%A0%E9%80%9F%E3%80%82
23. 掘金 — 跨国链路丢包总查不出来 (MTR/TCP traceroute methodology for cross-border links): https://juejin.cn/post/7631866320740663305
24. 腾讯云开发者 — 独立 App 配置 CDN 记录：腾讯云 CDN 加速阿里云 OSS (CORS + CDN configuration walkthrough): https://cloud.tencent.com.cn/developer/article/2709269
25. 掘金 — 深入浅出 GSLB (DNS redirect vs HTTP redirect vs Anycast; TTL/accuracy caveats): https://juejin.cn/post/7589839433321578559
26. Alibaba Cloud — DDoS 防护产品页 (20 Tbps global scrubbing network): https://www.aliyun.com/product/anti-ddos
27. Alibaba Cloud Help — 什么是DDoS高防 (mainland vs non-mainland products, security-acceleration line): https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/
28. CSDN — 阿里云国际站服务器高防是什么意思 (Anti-DDoS Pro vs Premium for mainland-origin + overseas-users; 保底+弹性 billing; hide origin IP): https://blog.csdn.net/2301_81684960/article/details/160138801
29. DNS666 — 国密证书部署前域名解析与ICP备案的确认要点 (ICP filing is prerequisite for mainland services/certs): https://www.dns666.com/gonggaotongzhi/4331.html
30. 掘金 — 等保密评的SSL证书如何申请 (Let's Encrypt vs domestic CA, DV certs for MLPS, TLS 1.2+): https://juejin.cn/post/7496404298583080997
31. 头条 — 2026国密SSL证书详解 (when SM2 certs are mandatory; dual-cert deployment): https://m.toutiao.com/group/7664438634782720566/
32. ZoTrus — 国密HTTPS加密自动化网关 (dual international+SM2 certificate architecture): https://dl.zotrus.com/pdf/ZoTrus_SM2_HTTPS_Gateway_Manual_CN-202303.pdf
33. 小月IDC — 香港服务器免备案+BGP大宽带 (HK no-ICP policy, latency numbers): https://www.xiaoyueidc.com/news/detail/article/7990
34. CSDN — 香港服务器深度测评：AWS vs 阿里云 vs GCP (HK CN2 GIA latency 30–50ms, no ICP, outbound-compliance notes): https://blog.csdn.net/awscloud/article/details/146147956
35. IDC.net — 香港服务器能否跑CRM系统 (CRM on HK servers: latency, compliance, optimization): https://idc.net/help/442395/
