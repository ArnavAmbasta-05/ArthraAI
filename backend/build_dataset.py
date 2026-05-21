"""
build_dataset.py — Generate ArthraAI training dataset

Run ONCE before train_model.py:
    python build_dataset.py

Outputs (written to project root):
    bias_data.csv       — full 2400-example dataset
    train.csv           — 70% split  (1680 rows)
    val.csv             — 15% split  (360 rows)
    test.csv            — 15% split  (360 rows)
    summarisation.csv   — (text, summary) pairs for flan-t5 fine-tuning

Dataset composition:
    800 Bullish  (bias_score 74-97)  label_id=2
    800 Bearish  (bias_score 1-26)   label_id=0
    800 Neutral  (bias_score 38-66)  label_id=1

Coverage:
    - Indian market indices (Sensex, Nifty, BSE, NSE)
    - Indian corporates (Reliance, Infosys, HDFC, TCS, etc.)
    - Macro / RBI / SEBI policy language
    - Global markets (S&P, Nasdaq, Fed, crude, gold)
    - Analyst language (upgrades, downgrades, targets)
    - Insider trading signals (OpenInsider-style)
"""

import random
import pandas as pd
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent

# ══════════════════════════════════════════════════════════
# RAW EXAMPLES
# (text, bias_score) — label derived from score automatically
# ══════════════════════════════════════════════════════════

BULLISH = [
    # Indian indices — price action
    ("Sensex surged 1200 points led by banking and IT stocks as FII inflows hit monthly high", 85),
    ("Nifty 50 rallied to fresh record high extending winning streak to eight consecutive sessions", 90),
    ("BSE Midcap index soared 3.2% as domestic institutional investors poured money into quality names", 83),
    ("Nifty Bank jumped 1800 points after RBI governor signalled end of rate hike cycle", 88),
    ("Indian equities climbed sharply as rupee strengthened to best level in six months", 80),
    ("Smallcap index skyrocketed 4% led by defence and infrastructure plays after budget boost", 87),
    ("Sensex rebounded from early losses to close 600 points higher on strong global cues", 78),
    ("Nifty IT index surged 5% after Infosys and TCS both beat quarterly revenue expectations", 92),
    ("Markets scaled new peaks as foreign portfolio investors turned net buyers for third week", 86),
    ("Indian equities rose sharply after US Fed signalled pause in rate hikes boosting risk appetite", 82),
    # Indian corporates
    ("Reliance Industries hits all-time high after JioFinancial partnership exceeds Street estimates", 91),
    ("Infosys beats Q4 estimates by 8% and raises FY25 revenue guidance to upper end of band", 93),
    ("HDFC Bank reports record net interest income as loan growth accelerates to 18% year on year", 89),
    ("TCS wins multi-billion dollar cloud transformation deal from European banking consortium", 87),
    ("ICICI Bank shares surge after net profit jumps 25% beating all analyst forecasts", 90),
    ("Bajaj Finance raises guidance after record customer additions in third consecutive strong quarter", 85),
    ("Adani Ports reports best-ever quarterly volumes driven by strong exports and container traffic", 84),
    ("Maruti Suzuki hits record monthly sales led by SUV segment and robust rural demand", 88),
    ("Wipro bags 500 million dollar five-year managed services contract from US healthcare major", 83),
    ("Asian Paints posts double-digit volume growth as raw material tailwinds ease margin pressure", 79),
    # Global bullish
    ("US economy adds 350000 jobs beating forecasts as unemployment falls to 50-year low", 88),
    ("Fed signals rate cuts possible in H2 as inflation trajectory improves significantly", 86),
    ("Nasdaq composite surges 3% after strong tech earnings led by Nvidia and Microsoft", 91),
    ("S&P 500 hits record high as corporate earnings season beats expectations across all sectors", 89),
    ("Apple reports blowout quarter with iPhone sales surging 15% ahead of all analyst estimates", 93),
    ("Goldman Sachs upgrades Indian equities to overweight citing 18% upside to target price", 90),
    ("Strong PMI data from US and Europe signal global manufacturing recovery gaining traction", 82),
    ("Oil prices rally 4% on OPEC production cut extension boosting energy sector broadly", 80),
    ("China stimulus package lifts Asian markets as property sector stabilisation hopes rise", 78),
    ("Tesla deliveries beat Wall Street estimates for third straight quarter on Model Y demand", 87),
    # Analyst / upgrade language
    ("Morgan Stanley initiates Nifty with overweight rating and December target of 25000", 85),
    ("Nomura raises Reliance target price by 20% citing JioFinancial growth acceleration", 88),
    ("BofA upgrades IT sector to overweight as rupee depreciation tailwinds favour exporters", 84),
    ("Strong buy consensus on HDFC Bank after six analyst upgrades in single week", 92),
    ("Macquarie raises Nifty target to 24500 on strong earnings momentum and macro stability", 86),
    ("UBS upgrades India to top pick in Asia citing structural growth and improving ROEs", 90),
    ("Earnings upgrades across Nifty 50 at fastest pace in three years signal broad recovery", 83),
    ("Buy rating maintained on Bajaj Finance with raised target on strong credit cycle", 87),
    ("CLSA upgrades entire Indian banking sector on improving asset quality and credit growth", 85),
    ("Jefferies initiates Maruti with buy citing EV readiness and rural market dominance", 81),
    # Macro bullish
    ("India GDP growth forecast raised to 7.2% by IMF on strong domestic consumption and capex", 89),
    ("FII inflows into India touch 8 billion dollars in single month highest since 2020", 91),
    ("India manufacturing PMI hits 16-year high at 59.1 signalling strong industrial expansion", 88),
    ("GST collections surpass 2 trillion rupees for fourth consecutive month beating all forecasts", 85),
    ("Record SIP inflows of 20000 crore signal retail investor confidence in India growth story", 87),
    ("India overtakes UK to become fifth largest economy ahead of schedule say economists", 90),
    ("Corporate earnings upgrades outnumber downgrades by 4 to 1 ratio best since 2007", 83),
    ("India infrastructure spending set for 11 trillion rupee capex cycle over next three years", 86),
    ("Digital payments volume in India hits record 14 billion transactions in single month", 82),
    ("India services exports hit all time high driven by IT GCC and fintech sector strength", 84),
]

BEARISH = [
    # Indian indices — price action
    ("Sensex crashes 1500 points as FII selling intensifies amid global risk-off sentiment", 12),
    ("Nifty 50 plunges below key 21000 support level on heavy selling across all sectors", 8),
    ("Indian markets tumble as rupee weakens sharply and RBI intervention fails to stem decline", 15),
    ("BSE Midcap index collapses 4% as investors flee to safety on global growth fears", 10),
    ("Nifty Bank slumps 900 points after RBI raises concern over rising NPAs in system", 14),
    ("Sensex suffers worst weekly decline in two years as foreign investors dump equities", 6),
    ("Markets crater at open as poor IIP data raises stagflation concerns among analysts", 18),
    ("Indian equities hit six-month low as inflation data surprises sharply on the upside", 12),
    ("FII outflows from India hit 12-month high as dollar strengthens and risk appetite fades", 9),
    ("Smallcap index nosedives 5% as overvaluation concerns trigger broad profit booking", 11),
    # Indian corporates
    ("Infosys cuts revenue guidance citing weak demand from BFSI clients and pricing pressure", 10),
    ("Wipro issues profit warning as deal wins disappoint and margins shrink further", 14),
    ("Yes Bank shares collapse after auditors flag divergence in NPA recognition practices", 6),
    ("Reliance Jio subscriber growth slows sharply raising questions about ARPU trajectory", 22),
    ("Zomato shares plunge after platform fee controversy triggers heavy user backlash", 15),
    ("Paytm stock crashes to record low after RBI action on payments bank operations", 5),
    ("Vodafone Idea shares tank after promoters refuse to inject fresh equity into company", 12),
    ("ONGC earnings miss badly as higher taxes offset any global crude rally benefit", 20),
    ("Hindustan Unilever volume growth disappoints for third straight quarter on rural slowdown", 18),
    ("HDFC Bank NIM compression worse than expected as deposit costs rise faster than loans", 22),
    # Global bearish
    ("US inflation re-accelerates to 3.8% forcing markets to price out Fed rate cuts entirely", 10),
    ("Nasdaq falls into correction territory as tech valuations face sustained multiple compression", 14),
    ("US regional banks face deposit flight crisis as commercial real estate losses mount", 8),
    ("China GDP growth disappoints at 4.2% as property sector crisis drags broader economy", 16),
    ("Global recession probability raised to 45% by IMF citing tighter financial conditions", 10),
    ("Fed signals higher for longer rates after inflation proves stickier than expected", 18),
    ("Crude oil collapses 8% as demand outlook deteriorates on weak manufacturing PMI globally", 12),
    ("European Central Bank warns of fragmentation risk as bond spreads widen sharply", 14),
    ("Wall Street banks slash bonus pools after worst year for dealmaking since 2008 crisis", 10),
    ("Tesla deliveries miss badly as EV demand slows and aggressive price cuts fail to boost volumes", 16),
    # Analyst / downgrade language
    ("Goldman Sachs downgrades Indian IT sector citing earnings risk and excessive valuation concern", 18),
    ("Moodys cuts outlook for Indian banking sector to negative on rising credit costs forecast", 12),
    ("Kotak downgrades Nifty target by 12% citing slower-than-expected earnings recovery ahead", 15),
    ("Sell rating initiated on HDFC Bank after disappointing deposit growth figures emerge", 20),
    ("Credit Suisse warns of systemic risk in Indian NBFC sector after liquidity squeeze", 8),
    ("Citi downgrades entire midcap space citing excessive valuations and earnings risk", 14),
    ("Bear case scenario for Sensex puts fair value 20% below current levels say analysts", 16),
    ("Multiple downgrades in auto sector after weak sales data disappoints for third month", 18),
    ("JPMorgan cuts India weight in EM portfolio citing currency risk and macro headwinds", 12),
    ("Jefferies lowers Nifty target as earnings upgrade cycle reverses more sharply than expected", 20),
    # Macro bearish
    ("India current account deficit widens sharply on higher oil import bill weighing on rupee", 22),
    ("RBI emergency measures fail to contain rupee slide against surging US dollar", 10),
    ("India inflation unexpectedly rises to 6.8% breaching RBI upper tolerance band", 15),
    ("GST revenue misses estimates for second consecutive month raising fiscal deficit concerns", 18),
    ("Foreign exchange reserves fall to lowest level in two years on heavy RBI intervention", 12),
    ("India trade deficit hits record high as export growth collapses and imports surge", 8),
    ("Retail investor margin calls spike as smallcap index enters technical bear market territory", 14),
    ("India sovereign bond yields spike 30 basis points on fiscal slippage and supply concerns", 18),
    ("Banking system liquidity deficit widens sharply as advance tax outflows hit hard", 16),
    ("India unemployment rate rises to 8.1% highest in 16 months on slowing job creation", 20),
]

NEUTRAL = [
    # Balanced policy and macro
    ("RBI holds repo rate at 6.5% as widely expected and maintains withdrawal of accommodation", 50),
    ("Markets trade flat ahead of key US inflation data as investors remain cautious on direction", 52),
    ("Nifty 50 ends marginally lower as gains in IT offset losses in banking and metals", 48),
    ("India Q3 GDP comes in at 6.4% in line with consensus estimates with consumption mixed", 50),
    ("Sensex trades in tight range as domestic factors balance against global uncertainty broadly", 51),
    ("Markets mixed after Fed minutes show divided opinion on pace and scale of future rate cuts", 49),
    ("IT sector cautious as clients defer discretionary spending while deal pipeline remains intact", 47),
    ("Rupee holds steady near 83 to dollar as RBI and global factors remain broadly in balance", 50),
    ("Q4 earnings season begins with results broadly in line with reduced analyst consensus estimates", 52),
    ("Sebi announces consultation paper on algo trading and industry response remains mixed overall", 50),
    # Company results in line
    ("Infosys reports quarterly results in line with estimates with guidance unchanged at midpoint", 50),
    ("HDFC Bank deposits grow 16% while loan growth moderates to 15% and spread is maintained", 51),
    ("TCS revenue growth of 6% meets consensus as management commentary balanced on outlook", 49),
    ("Wipro Q3 results in line with sequential revenue guidance of flat to 1% growth maintained", 50),
    ("Reliance Q3 Ebitda meets estimates as Jio grows steadily while retail shows some moderation", 52),
    ("Bajaj Finance AUM grows 28% year on year while credit costs slightly above earlier guidance", 48),
    ("Auto sector sales data mixed with passenger vehicles growing 8% while commercial vehicles flat", 50),
    ("FMCG volume growth improves marginally to 4% though urban rural divergence persists broadly", 51),
    ("Pharma sector results split as US business recovers while domestic formulations slow somewhat", 49),
    ("Banking sector credit growth at 14% remains steady but deposit competition intensifies further", 50),
    # Policy neutral
    ("Union Budget maintains fiscal consolidation path with moderate increase in capex allocation", 51),
    ("RBI monetary policy committee vote split 4-2 on rate decision reflecting genuine uncertainty", 49),
    ("India inflation at 5.1% above RBI 4% target but within 6% upper band with stable trajectory", 50),
    ("Trade data shows export improvement offset by import surge leaving deficit broadly stable", 52),
    ("Sebi tightens F&O rules and analyst views divided on near-term market volume impact", 48),
    ("India PMI manufacturing at 54.5 signals expansion but pace of growth moderates slightly", 51),
    ("RBI annual report flags both upside and downside risks in balanced assessment of economy", 50),
    ("Credit rating agencies maintain stable outlook on India while noting key risks to watch", 52),
    ("Foreign portfolio flows neutral in month as buying in financials offsets selling in IT", 49),
    ("India WPI inflation falls to 2.1% while CPI stays elevated creating complex policy situation", 50),
    # Global neutral
    ("Fed holds rates steady as expected and dot plot shows two cuts this year with uncertainty", 50),
    ("US Q2 GDP growth of 2.1% meets consensus as consumption solid but investment spending soft", 51),
    ("Oil prices range-bound between 80 and 85 as OPEC cuts offset by rising US shale output", 49),
    ("Global PMI data mixed with services expanding while manufacturing remains in contraction", 50),
    ("Asian markets trade mixed as China stimulus hopes balanced against property sector fears", 48),
    ("Dollar index holds flat as markets weigh conflicting signals on US growth and inflation", 51),
    ("European growth barely positive as German industrial production disappoints marginally", 49),
    ("Emerging market flows stabilise after volatility with India and Brazil seeing modest inflows", 52),
    ("Commodity prices mixed with metals up and agricultural goods declining on supply normalisation", 50),
    ("G20 finance ministers communique acknowledges global growth risks but avoids specific targets", 50),
    # Insider signals — neutral-ish
    ("Director of HDFC Bank purchases 5000 shares at market price signalling personal confidence", 60),
    ("Infosys CEO exercises stock options and immediately sells shares as part of planned programme", 45),
    ("Promoter of Tata Motors increases stake by 0.2% in open market purchase worth 8 crore", 62),
    ("Independent director of Bajaj Finance sells shares citing personal financial planning needs", 42),
    ("Insider purchases at Reliance by three board members totalling 15 crore rupees this quarter", 63),
    ("MD of ICICI Bank disposes RSUs as per scheduled vesting and pre-announced sale programme", 48),
    ("Minor insider purchase at Wipro reported at current market prices per regulatory filing", 58),
    ("Promoter group of Asian Paints trims stake by 0.1% in block deal at marginal discount", 44),
    ("Institutional insider at SBI buys shares worth 5 crore rupees in open market transaction", 60),
    ("Board member sells shares post quarterly results as part of pre-announced divestment plan", 46),
]

# ══════════════════════════════════════════════════════════
# AUGMENTATION — expand to 800 per class
# ══════════════════════════════════════════════════════════
_AUGMENTS = [
    lambda t: t + ", analysts say",
    lambda t: t + " on heavy trading volumes",
    lambda t: t + " amid global market moves",
    lambda t: t + " per exchange data",
    lambda t: t + " in early trade today",
    lambda t: t + " traders note cautiously",
    lambda t: t + " according to market sources",
    lambda t: t + " as per latest data",
    lambda t: "Breaking: " + t,
    lambda t: "Markets update: " + t,
    lambda t: "Market wrap: " + t,
    lambda t: "Live update: " + t,
]


def augment(examples: list, target: int = 800) -> list:
    result = list(examples)
    while len(result) < target:
        base_text, base_score = random.choice(examples)
        mod = random.choice(_AUGMENTS)
        try:
            new_text = mod(base_text)
        except Exception:
            new_text = base_text
        jitter   = random.randint(-4, 4)
        new_score = max(0, min(100, base_score + jitter))
        result.append((new_text, new_score))
    return result[:target]


# ══════════════════════════════════════════════════════════
# BUILD FULL DATASET
# ══════════════════════════════════════════════════════════
def build():
    bull_aug = augment(BULLISH, 800)
    bear_aug = augment(BEARISH, 800)
    neut_aug = augment(NEUTRAL, 800)

    rows = []
    for text, score in bull_aug:
        rows.append({"text": text, "label": "Bullish", "bias_score": score, "label_id": 2})
    for text, score in bear_aug:
        rows.append({"text": text, "label": "Bearish", "bias_score": score, "label_id": 0})
    for text, score in neut_aug:
        rows.append({"text": text, "label": "Neutral", "bias_score": score, "label_id": 1})

    random.shuffle(rows)
    df = pd.DataFrame(rows)

    # Save full dataset
    out = BASE_DIR / "bias_data.csv"
    df.to_csv(out, index=False)
    print(f"✅ bias_data.csv saved — {len(df)} rows")

    # Train / val / test split: 70 / 15 / 15
    n       = len(df)
    n_train = int(n * 0.70)
    n_val   = int(n * 0.15)

    train_df = df.iloc[:n_train]
    val_df   = df.iloc[n_train:n_train + n_val]
    test_df  = df.iloc[n_train + n_val:]

    train_df.to_csv(BASE_DIR / "train.csv", index=False)
    val_df.to_csv(BASE_DIR / "val.csv",   index=False)
    test_df.to_csv(BASE_DIR / "test.csv", index=False)

    print(f"   train.csv : {len(train_df)} rows")
    print(f"   val.csv   : {len(val_df)} rows")
    print(f"   test.csv  : {len(test_df)} rows")

    # Label distribution
    print("\nLabel distribution (full):")
    print(df["label"].value_counts().to_string())
    print("\nScore ranges by label:")
    print(df.groupby("label")["bias_score"].agg(["mean", "min", "max"]).round(1).to_string())

    # ── Summarisation dataset (for flan-t5 fine-tuning) ──
    summ_rows = []
    templates = {
        "Bullish": [
            "Bullish market sentiment reported. {t}",
            "Positive financial development: {t}",
            "Market gains noted as: {t}",
        ],
        "Bearish": [
            "Bearish market conditions reported. {t}",
            "Financial decline observed: {t}",
            "Market weakness recorded as: {t}",
        ],
        "Neutral": [
            "Balanced market development reported. {t}",
            "Neutral financial update: {t}",
            "Mixed market conditions: {t}",
        ],
    }
    for _, row in df.iterrows():
        tpl = random.choice(templates[row["label"]])
        summ_rows.append({
            "input":  f"summarize financial news: {row['text']}",
            "target": tpl.format(t=row["text"][:120]),
            "label":  row["label"],
        })

    summ_df = pd.DataFrame(summ_rows)
    summ_df.to_csv(BASE_DIR / "summarisation.csv", index=False)
    print(f"\n✅ summarisation.csv saved — {len(summ_df)} rows")
    print("\n🎉 Dataset build complete. Run train_model.py next.")


if __name__ == "__main__":
    build()