# The Mathematics of a World Cup Prediction Model

### A worked case study in multi-criteria scoring, logistic choice models, discrete probability, and Monte Carlo simulation

---

## How to read this document

You do not need to know anything about football, FIFA, or the World Cup to
follow this document. Every concept here is a standard tool from statistics,
probability, or applied mathematics — the "World Cup" is simply the dataset
and the motivating story. If anything, treat the 48 national teams as 48
unlabeled objects, each described by an 11-dimensional feature vector, and
the question is: *given a user-chosen weighting of those 11 features, what is
the probability distribution over which object "wins" a randomized
single-elimination tournament with a 12-group round-robin qualifying stage?*

Every section below states **what** is computed, **why** that particular
mathematical tool was chosen over the alternatives, and suggests a **figure**
that would help a reader build intuition. Formulas are given in standard
notation so they render correctly from Markdown into Word via Pandoc/LaTeX.

---

## 1. Overview of the pipeline

The model is a five-stage pipeline. Each stage is a separate mathematical
object, and the rest of this document devotes one section to each:

```
Raw data (11 features × 48 teams)
        │
        ▼
   [§2] Normalization        →  each feature rescaled to a comparable [0,1] scale
        │
        ▼
   [§3] Weighted aggregation  →  one scalar "Power Score" S_i per team
        │
        ▼
   [§4] Pairwise comparison    →  Power Score gap Δ → win probability & expected goals
        │
        ▼
   [§5] Discrete outcome model →  expected goals → an actual integer scoreline
        │
        ▼
   [§6–8] Tournament simulation → group stage + knockout bracket → a champion
        │
        ▼
   [§9] Monte Carlo aggregation → 2,000 repetitions → champion probability distribution
```

**Suggested Figure 1.1** — a horizontal flow diagram reproducing the pipeline
above, using the section numbers as labels, so the reader can use it as a
"map" while reading the rest of the document.

---

## 2. Stage 1 — Normalization: putting 11 incommensurable variables on one scale

### 2.1 The problem

Each of the 48 teams is described by **11 raw features**, e.g.:

| Feature | Example raw values | Native units |
|---|---|---|
| Elo rating | 1850 – 2171 | rating points |
| FIFA ranking points | ~900 – ~1850 | points |
| Squad quality (EA Sports rating) | ~70 – ~87 | 0–99 scale |
| Betting market implied win probability | 0.01 – 0.16 | probability |
| World Cup titles/appearances/best finish | composite | counts & ranks |
| Total GDP | $2.7B – $28.75T | US dollars |
| Population | 156,000 – 340,000,000 | people |
| Travel distance between venues | ~5,000 – ~12,600 | km |
| Heat disadvantage | small positive/negative | °C |
| Home-confederation membership | yes/no | binary |

These cannot be combined directly — a one-unit change in "GDP" and a
one-unit change in "Elo rating" are not comparable, and some features are
"higher is better" while others are "lower is better." The model needs a
function

$$
f_k : \mathbb{R} \to [0,1]
$$

for each feature $k$, mapping every team's raw value $x_{i,k}$ to a
normalized value $f_{i,k} = f_k(x_{i,k}) \in [0,1]$, where **1 always means
"best for that feature, relative to the current 48-team pool"** and **0
always means "worst."** This is a classic step in **multi-criteria decision
analysis (MCDA)** — specifically, this whole model is an instance of the
**Simple Additive Weighting (SAW)** method, also called a *weighted sum
model*, which is one of the oldest and most widely used MCDA techniques.

Five different normalization strategies are used, one per "shape" of
variable. The rest of this section justifies each one.

---

### 2.2 Linear min–max normalization (the default)

For a feature vector $\mathbf{x} = (x_1, \dots, x_{48})$ across the team
pool, define

$$
f(x_i) = \frac{x_i - \min(\mathbf{x})}{\max(\mathbf{x}) - \min(\mathbf{x})}
$$

(with the convention that if $\max(\mathbf{x}) = \min(\mathbf{x})$, the
denominator is replaced by $1$ to avoid division by zero — a degenerate edge
case that never actually arises with 48 distinct teams, but is handled for
robustness).

**Used for:** Elo rating, FIFA ranking points, squad quality, league
strength, betting-market implied probability, and the tournament-experience
composite score (§2.5).

**Why this is the right default:** these are all variables where:

1. The *range* across the 48-team pool is itself the meaningful scale — a
   team's Elo rating only matters in comparison to the other 47 teams in this
   tournament, not in absolute "Elo points since 1850" terms.
2. The variables are **not heavy-tailed** — ratings, percentages, and 0–99
   scores are roughly uniformly spread across their range, so a linear
   rescaling preserves the *relative spacing* between teams. A team in the
   middle of the Elo distribution stays in the middle of $[0,1]$ after
   normalization.

Formally, linear min-max normalization is an **affine transformation**
$f(x) = a x + b$ with $a = 1/(\max-\min) > 0$ and $b = -\min/(\max-\min)$. An
affine transformation preserves ratios of *differences*: if team A is twice
as far from team B as team B is from team C on the raw scale, that remains
true after normalization. This is exactly the property you want when "twice
the gap" should mean "twice the gap" in the final score.

**Suggested Figure 2.1** — a number line showing raw Elo ratings (1840 to
2171) for a handful of teams as dots, with a second number line directly
below showing the same teams' positions after min-max normalization to
$[0,1]$ — visually demonstrating that linear normalization is just a "stretch
and shift," preserving relative spacing.

---

### 2.3 Log-scale min–max normalization — for heavy-tailed, multiplicative variables

**Used for:** total GDP and total population.

#### 2.3.1 Why linear min-max fails here

Population across the 48 teams ranges from about **156,000** (Curaçao) to
**340,000,000** (USA) — a ratio of about **2,180×**. GDP ranges from about
**$2.7 billion** to **$28.75 trillion** — a ratio of about **10,500×**.

These variables are **heavy-tailed**: a small number of very large
countries/economies are enormously larger than the typical team in the pool.
If $X$ is heavy-tailed (think log-normal or Pareto-like, which is the
standard stylized fact for both population and GDP across countries — this
is the same family of distributions behind Zipf's law for city sizes), then
applying linear min-max normalization

$$
f(x) = \frac{x - \min(\mathbf{x})}{\max(\mathbf{x}) - \min(\mathbf{x})}
$$

produces a normalized variable where **almost every team is squeezed into a
tiny interval near 0**, because the denominator $\max(\mathbf{x}) -
\min(\mathbf{x})$ is dominated by the single largest value (the USA's
population).

Concretely, this happened in an earlier version of this model: Germany's
83.5 million people, linearly normalized against the pool ($156{,}000$ to
$340{,}000{,}000$), mapped to $f = 0.245$ — even though Germany has **536
times** Curaçao's population. The model's downstream "expected goals" formula
(§4.2) then read this $0.245$ gap as a *modest* advantage, producing
underwhelming results (a simulated Germany 2–1 vs. Curaçao when "solo-ing"
the population factor) that did not reflect the enormous real-world disparity.

#### 2.3.2 The fix: normalize the logarithm

Instead, define

$$
f(x_i) = \frac{\log_{10}(x_i) - \min_j \log_{10}(x_j)}{\max_j \log_{10}(x_j) - \min_j \log_{10}(x_j)}
$$

i.e., **apply linear min-max normalization to $\log_{10}(x)$ instead of $x$
itself.**

#### 2.3.3 Why this is the correct mathematical choice

This is best understood as an instance of the **Weber–Fechner law** from
psychophysics: the *perceived* magnitude of a stimulus is proportional to the
*logarithm* of its physical magnitude, not its raw magnitude. A country with
20 million people does not "feel" twice as significant as a country with 10
million in the same way that 20 kg feels twice as heavy as 10 kg on a scale —
but a country with 200 million people *does* feel like it's in a qualitatively
different "tier" than one with 20 million. Order-of-magnitude differences are
what carry information for these variables, not absolute differences.

Taking the logarithm converts a **multiplicative** scale into an **additive**
one:

$$
\log_{10}(2x) - \log_{10}(x) = \log_{10}(2) \approx 0.301 \quad \text{for any } x
$$

That is, *doubling* a country's population always produces the **same
additive shift** in $\log_{10}(\text{population})$, regardless of whether the
comparison is 1 million → 2 million or 100 million → 200 million. After this
transformation, min-max normalization spreads the 48 teams roughly evenly
across $[0,1]$ instead of collapsing 47 of them near 0.

**Verified result:** after this change, Germany's normalized population went
from $0.245 \to 0.817$ (Curaçao remains at $0.0$, since it is still the pool
minimum on a log scale too — log is monotonic, so it never changes *which*
team is the min or max, only the *spacing* between them). The "solo
population" simulation of Germany vs. Curaçao changed from **2–1** to **6–0**
— a result that finally reflects the 536× real-world gap in a way the
downstream exponential model (§4.2) can express.

**Suggested Figure 2.2** — a two-panel comparison plot. Left panel: all 48
teams' raw populations plotted on a linear x-axis, with the linear-min-max
normalized value on the y-axis — showing 47 of 48 points crammed near $y=0$
with only the USA near $y=1$. Right panel: the same 48 teams, but with
$\log_{10}(\text{population})$ on the x-axis and the log-normalized value on
the y-axis — showing a roughly even spread across $[0,1]$. This single figure
is probably the most important visual in the whole document for conveying
*why* this normalization choice matters.

---

### 2.4 Inverted normalization — for "lower is better" variables

**Used for:** travel distance between tournament venues, and "heat
disadvantage" (the climate gap between a squad's home leagues and the World
Cup host cities).

For these variables, a **smaller** raw value is better (less travel fatigue,
less heat disadvantage). The fix is simply to flip the direction after
min-max normalizing:

$$
f(x_i) = 1 - \frac{x_i - \min(\mathbf{x})}{\max(\mathbf{x}) - \min(\mathbf{x})}
 \;=\; \frac{\max(\mathbf{x}) - x_i}{\max(\mathbf{x}) - \min(\mathbf{x})}
$$

This is still an affine transformation (now with negative slope
$a = -1/(\max-\min)$), so it preserves the same "evenly spread, ratio of
differences preserved" properties as §2.2 — it is min-max normalization
composed with the reflection $y \mapsto 1-y$. The team with the *shortest*
travel distance gets $f = 1$ (full marks), and the team with the longest gets
$f = 0$.

**Suggested Figure 2.3** — a simple diagram showing the transformation
$x \mapsto 1 - \frac{x-\min}{\max-\min}$ as a reflection of the standard
min-max line — e.g., overlay the "higher is better" line from Figure 2.1 and
this "lower is better" line on the same axes, mirrored about $y=0.5$.

---

### 2.5 Composite (derived) scores, then linearly normalized

**Used for:** "Tournament Experience."

Some factors are not single raw measurements but **engineered composite
indices** — a weighted combination of several raw sub-variables, computed
*before* normalization. Tournament Experience is built as:

$$
E_i^{\text{raw}} = 3 \cdot (\text{World Cup titles}_i) + 0.5 \cdot (\text{World Cup appearances}_i) + (9 - \text{best\_finish}_i)
$$

where $\text{best\_finish} \in \{1, \dots, 8\}$ (1 = winner, 8 = never
qualified), so $(9 - \text{best\_finish}) \in \{1,\dots,8\}$ with higher
being better.

This raw composite score is *itself* a simple additive (weighted-sum) model —
a small-scale version of the overall Power Score model in §3 — reflecting the
modeler's judgment that titles are worth roughly $3/0.5 = 6\times$ as much as
a single additional appearance, and that reaching a final (best\_finish $=2$,
contributing $7$) is worth more than not qualifying at all
(best\_finish $=8$, contributing $1$).

Once $E_i^{\text{raw}}$ is computed for all 48 teams, it is linearly min-max
normalized exactly as in §2.2:

$$
f^{\text{experience}}_i = \frac{E_i^{\text{raw}} - \min_j E_j^{\text{raw}}}{\max_j E_j^{\text{raw}} - \min_j E_j^{\text{raw}}}
$$

This two-level structure — *engineer a raw composite, then normalize* — is a
common pattern when a single "real" measurement does not exist but several
correlated proxies do.

---

### 2.6 Binary indicator variables — no normalization needed

**Used for:** Home-confederation advantage.

$$
f^{\text{home}}_i = \begin{cases} 1 & \text{team } i \text{ belongs to the host confederation (CONCACAF for 2026)} \\ 0 & \text{otherwise} \end{cases}
$$

This is already an element of $[0,1]$ (in fact of $\{0,1\} \subset [0,1]$),
so no transformation is applied. Mathematically, this is a **Bernoulli
indicator variable** / dummy variable for a categorical condition — the
simplest possible "normalization" is the identity map, which is valid
precisely because the raw variable was already binary-categorical rather than
continuous.

---

### 2.7 Regression-based estimation for missing data — FIFA ranking points

**Used for:** FIFA World Ranking points, for the subset of teams (about
two-thirds of the 48) for which an official figure is not readily available.

This is a slightly different kind of problem: it's not about *rescaling* a
variable, but about **filling in missing values** before any normalization
can happen at all.

#### 2.7.1 The approach: simple linear regression (ordinary least squares)

Among the teams *with* known FIFA points, fit a simple linear model against
Elo rating (a closely related, fully-available rating system):

$$
\text{fifa\_points} = \beta_0 + \beta_1 \cdot \text{elo\_rating} + \varepsilon
$$

estimated by ordinary least squares (minimizing $\sum_i \varepsilon_i^2$) over
the teams with known FIFA points, giving estimates $\hat\beta_0, \hat\beta_1$.
For every team *without* an official FIFA points figure, the missing value is
imputed as:

$$
\widehat{\text{fifa\_points}}_i = \hat\beta_0 + \hat\beta_1 \cdot \text{elo\_rating}_i
$$

**Why this is reasonable:** Elo rating and FIFA ranking points are both
long-run, results-based rating systems computed from largely the same
underlying match results, using different formulas and weightings. They are
*highly correlated* (this is exactly the kind of situation single-variable
linear regression is designed for: predicting one variable from another
strongly correlated one). A provenance flag
(`fifa_rank_source ∈ {"official", "estimated"}`) is retained for every team,
so the imputation is fully auditable and could later be replaced by a live
data feed without changing the model's structure.

Once every team has a `fifa_points` value (official or estimated), the
feature is linearly min-max normalized exactly as in §2.2.

**Suggested Figure 2.4** — a scatter plot of Elo rating (x-axis) vs. FIFA
points (y-axis) for the teams with official data, with the fitted regression
line overlaid, and the imputed points for the "estimated" teams shown in a
different color/marker sitting on the line. This is a nice, self-contained
illustration of OLS regression and imputation in one picture.

---

### 2.8 Summary table of normalization choices

| Factor | Normalization | Direction | Why |
|---|---|---|---|
| Elo rating | Linear min-max | higher = better | roughly uniform spread; relative rank within pool is what matters |
| FIFA ranking points | Regression-imputed, then linear min-max | higher = better | ~2/3 of values missing; Elo is a strong predictor |
| Squad quality | Linear min-max | higher = better | bounded 0–99 rating scale, roughly uniform |
| League strength | Linear min-max | higher = better | same as above |
| Betting market probability | Linear min-max | higher = better | already a probability, roughly uniform across pool |
| Tournament experience | Composite index → linear min-max | higher = better | engineered weighted sum of titles/appearances/best-finish |
| Home-confederation advantage | None (already binary) | 1 = host confederation | categorical, not continuous |
| GDP | **Log-scale min-max** | higher = better | heavy-tailed, >4 orders of magnitude span |
| Population | **Log-scale min-max** | higher = better | heavy-tailed, >3 orders of magnitude span |
| Travel distance | Inverted linear min-max | lower raw = higher score | "less travel is better" |
| Heat disadvantage | Inverted linear min-max | lower raw = higher score | "less climate disruption is better" |

At the end of this stage, every team $i$ has an **11-dimensional feature
vector** $\mathbf{f}_i = (f_{i,1}, \dots, f_{i,11}) \in [0,1]^{11}$.

---

## 3. Stage 2 — The Power Score: a weighted sum (convex combination)

### 3.1 Weight normalization — projecting onto the simplex

The user supplies 11 raw "importance" weights $w_1^{\text{raw}}, \dots,
w_{11}^{\text{raw}}$ (each a slider value, conceptually in $[0, 100]$, though
the math places no upper bound on them). These are converted into a
**probability vector** — a point on the **standard simplex**
$\Delta^{10} = \{ w \in \mathbb{R}^{11}_{\ge 0} : \sum_k w_k = 1 \}$ — via
simple $L^1$ normalization:

$$
w_k = \frac{w_k^{\text{raw}}}{\sum_{j=1}^{11} w_j^{\text{raw}}}, \qquad \text{provided } \sum_j w_j^{\text{raw}} > 0
$$

In the degenerate case $\sum_j w_j^{\text{raw}} \le 0$ (e.g. the user sets
every slider to zero), the model falls back to the **uniform distribution**
$w_k = 1/11$ for all $k$ — the centroid of the simplex, representing "no
information / treat all factors equally."

### 3.2 The Power Score formula

For each team $i$, the **Power Score** is the weighted sum:

$$
S_i = \sum_{k=1}^{11} w_k \, f_{i,k}
$$

This is precisely the **Simple Additive Weighting (SAW)** formula from
multi-criteria decision analysis — one of the oldest and most interpretable
ways to combine multiple normalized criteria into a single ranking score, and
mathematically identical to computing a **weighted average** of the 11
normalized features, with the weights summing to 1.

### 3.3 A convexity observation

Because $\mathbf{f}_i \in [0,1]^{11}$ (every normalized feature lies in
$[0,1]$) and $\mathbf{w}$ lies in the simplex $\Delta^{10}$ (all weights
non-negative, summing to 1), $S_i$ is a **convex combination** of 11 numbers
each in $[0,1]$. A standard and easy-to-prove fact about convex combinations
is:

$$
\min_k f_{i,k} \;\le\; S_i \;\le\; \max_k f_{i,k}
$$

and in particular $S_i \in [0,1]$ always — **the Power Score is guaranteed to
land in $[0,1]$ for *every* possible choice of weights**, with no clipping or
rescaling required. This is a direct, useful consequence of doing the
normalization step (§2) *before* the weighting step.

**Suggested Figure 3.1** — for a single example team, a horizontal stacked
bar chart showing the 11 terms $w_k f_{i,k}$ as segments of different widths
and colors, summing to $S_i$ — visually demonstrating "Power Score = weighted
sum of normalized factors" as a literal picture of the formula.

**Suggested Figure 3.2** — a bar chart ranking all 48 teams by $S_i$ for the
default weight configuration — the "Power Rankings" table that the
application surfaces to the user, presented as the direct output of this
section's formula.

---

## 4. Stage 3 — From a Power Score gap to a match outcome

Once every team has a single scalar $S_i \in [0,1]$, a match between team A
and team B is governed entirely by the **gap**

$$
\Delta = S_A - S_B \in [-1, 1]
$$

(bounded in $[-1,1]$ because both $S_A, S_B \in [0,1]$). Two independent
functions of $\Delta$ are computed: a **win probability** (used for
penalty-shootout resolution) and a pair of **expected goal counts** (used for
the scoreline itself).

### 4.1 Win probability — a logistic (Bradley–Terry / Elo-style) model

$$
P(A \text{ beats } B) = \frac{1}{1 + 10^{-\Delta \cdot K}}, \qquad K = 6.0
$$

This is the **same functional form as the Elo rating system's "expected
score" formula** (Arpad Elo, 1960s chess ratings, later adopted across
sports analytics): $E_A = \dfrac{1}{1+10^{-(R_A-R_B)/400}}$. Here $\Delta$
plays the role of the rating difference, and $K=6$ plays the role of the
$1/400$ scaling constant (just inverted and rescaled for the $[0,1]$ Power
Score range instead of the $[0, \sim 3000]$ Elo range). This family of models
is also known as the **Bradley–Terry model** for pairwise comparisons
(Bradley & Terry, 1952), widely used to convert a latent "strength" score for
each item into a probability that item A beats item B in head-to-head
competition.

Equivalently, writing $\sigma(x) = \frac{1}{1+e^{-x}}$ for the standard
logistic (sigmoid) function, $P(A \text{ beats } B) = \sigma(\Delta \cdot K
\ln 10)$ — base 10 is used purely for convenience/legacy from Elo's original
formula, and is mathematically equivalent to the natural-exponential logistic
function up to rescaling $K$.

**Properties:**
- $P(0) = \tfrac12$ — equal Power Scores ⟺ a coin-flip.
- Monotonically increasing and **symmetric**: $P(-\Delta) = 1 - P(\Delta)$.
- Saturates toward $0$ or $1$ for large $|\Delta|$. Since $|\Delta| \le 1$
  here, the theoretical range is
  $P \in \left(\frac{1}{1+10^{6}}, \frac{10^{6}}{1+10^{6}}\right) \approx
  (10^{-6},\ 1-10^{-6})$ — i.e. the model *can* express near-certainty for the
  largest possible gap, but treats it as overwhelmingly likely rather than
  mathematically impossible (a hallmark of a well-calibrated probabilistic
  model — "never say never").

**Worked examples** (computed directly from the formula):

| $\Delta$ | $P(A \text{ beats } B)$ |
|---|---|
| $0.00$ | $0.500$ |
| $0.05$ | $0.666$ |
| $0.10$ | $0.799$ |
| $0.20$ | $0.941$ |
| $0.30$ | $0.984$ |
| $0.50$ | $0.999$ |
| $0.82$ | $\approx 1.000$ |

A modest Power Score gap of just $0.1$ (out of a maximum possible $1.0$)
already implies an $80\%$ win probability — the logistic curve is quite
steep near the origin, controlled by $K=6$.

**Suggested Figure 4.1** — plot $P(\Delta)$ for $\Delta \in [-1, 1]$, a
classic "S-shaped" logistic curve, with the table above's points marked.
Annotate the curve to show how steep it is — e.g. shade the region
$\Delta \in [-0.2, 0.2]$ to show that most of the "interesting" probability
range $(0.06, 0.94)$ is compressed into this relatively narrow band of Power
Score gaps.

**Where this is used:** only for resolving **penalty shootouts** — when a
knockout match's regulation/extra-time score is tied (§5), the shootout
winner is decided by a single Bernoulli draw with success probability
$P(A \text{ beats } B)$.

---

### 4.2 Expected goals — a log-linear (exponential) model

For team $A$ playing team $B$, define $A$'s **expected number of goals**:

$$
\lambda_A = \min\Big( G \cdot e^{\,\gamma \Delta},\ \lambda_{\max} \Big), \qquad G = 1.35,\ \ \gamma = 2.2,\ \ \lambda_{\max} = 6.0
$$

and symmetrically $\lambda_B = \min(G \cdot e^{-\gamma\Delta}, \lambda_{\max})$
(note the sign flip on $\Delta$, since from $B$'s perspective the gap is
$-\Delta$).

#### 4.2.1 Why exponential, not linear?

A naive model might try $\lambda_A = G + \gamma \Delta$ (linear in the Power
Score gap). The problem: for a sufficiently negative $\Delta$ (a big
underdog), a linear model can produce **negative expected goals** — which is
nonsensical, since a count of goals must be non-negative.

The exponential form solves this structurally: $e^{\gamma\Delta} > 0$ for
*every* real $\Delta$, so $\lambda_A > 0$ always, **by construction**, with
no need for clipping at zero. This is exactly the reasoning behind the **log
link function** in a Poisson regression / generalized linear model (GLM):
modeling

$$
\log(\lambda) = \beta_0 + \beta_1 \Delta \quad\Longleftrightarrow\quad \lambda = e^{\beta_0} \cdot e^{\beta_1 \Delta}
$$

with $e^{\beta_0} = G = 1.35$ (the baseline expected goals between two
*exactly equal* teams, $\Delta=0$) and $\beta_1 = \gamma = 2.2$ (how strongly
a one-unit Power Score gap shifts the log-expected-goals). This log-linear
structure is the foundation of classical football forecasting models —
notably **Maher's (1982)** model, one of the earliest statistical models of
football scorelines, and its descendants such as the **Dixon–Coles (1997)**
model, both of which represent each team's scoring rate as the exponential of
a linear combination of "attack" and "defense" strength parameters.

#### 4.2.2 A reciprocal invariant

Before the cap $\lambda_{\max}$ is applied, observe:

$$
\lambda_A \cdot \lambda_B = G\,e^{\gamma\Delta} \cdot G\,e^{-\gamma\Delta} = G^2 = 1.35^2 = 1.8225
$$

**The product of the two teams' (uncapped) expected goals is a constant**,
independent of $\Delta$. As one team's expected goals rises (because it's the
stronger side), the other's falls *reciprocally*, keeping the product fixed.
This is a clean algebraic property worth highlighting — it shows the model is
"conserving" a kind of total goal-scoring potential between the two sides and
redistributing it according to the strength gap, rather than simply adding
goals to the stronger side for free.

#### 4.2.3 The cap $\lambda_{\max} = 6$

Without the cap, an extreme gap $\Delta = 1$ (the theoretical maximum) would
give $\lambda_A = 1.35 \cdot e^{2.2} \approx 12.2$ expected goals — wildly
unrealistic (a 12-goal margin essentially never happens in international
football). Capping at $\lambda_{\max}=6$ keeps the model within a realistic
range; 6 goals in a single match is already an extremely rare scoreline, so
it serves as a sensible ceiling. Once $\lambda_A$ hits the cap, the reciprocal
invariant from §4.2.2 breaks (the product is no longer constant), which is the
intended, deliberate behavior of a cap — it should *only* bind in extreme
cases.

**Worked examples:**

| $\Delta$ | $\lambda_A$ | $\lambda_B$ | $\lambda_A \cdot \lambda_B$ |
|---|---|---|---|
| $0.000$ | $1.350$ | $1.350$ | $1.8225$ |
| $0.100$ | $1.682$ | $1.083$ | $1.8225$ |
| $0.245$ | $2.314$ | $0.787$ | $1.8225$ |
| $0.500$ | $4.056$ | $0.449$ | $1.8225$ |
| $0.817$ | $6.000$ (capped) | $0.224$ | $1.3424$ |
| $1.000$ | $6.000$ (capped) | $0.150$ | $0.8975$ |

**Suggested Figure 4.2** — plot $\lambda_A(\Delta)$ and $\lambda_B(\Delta) =
\lambda_A(-\Delta)$ on the same axes for $\Delta \in [-1,1]$, two mirror-image
exponential curves that flatten out at $\lambda_{\max}=6$ for $|\Delta|$ near
$1$. Mark the crossing point at $\Delta=0$ where both equal $G=1.35$, and
shade the region where the cap is active.

---

## 5. Stage 4 — From expected goals to an actual scoreline: discrete distributions

Once $\lambda_A$ and $\lambda_B$ are computed, the model needs to draw **an
actual integer number of goals** for each side. This is the step where a
choice of *discrete probability distribution* matters most, and it's the
heart of the "Monte Carlo vs. Poisson" question.

### 5.1 The classical choice: the Poisson distribution

The standard model in football analytics for "number of goals scored in a
match" is the **Poisson distribution**:

$$
P(X = k) = \frac{e^{-\lambda}\lambda^k}{k!}, \qquad k = 0, 1, 2, \dots
$$

This arises naturally as the limiting distribution of a **Poisson process** —
a large number of independent, individually-unlikely "scoring opportunities"
over the 90 minutes of a match, each with a small probability of becoming a
goal (the **law of rare events** / Poisson limit theorem, formalized below in
§5.3). It is the basis of foundational football models such as Maher (1982).

A defining property of the Poisson distribution is **equidispersion**:

$$
\mathbb{E}[X] = \mathrm{Var}(X) = \lambda
$$

The mean and variance are *forced to be equal* — there is no free parameter
to make the distribution "tighter" or "wider" independently of its mean.

#### 5.1.1 Why this caused a problem for *this* model

This model's earlier version sampled $X_A \sim \mathrm{Poisson}(\lambda_A)$
and $X_B \sim \mathrm{Poisson}(\lambda_B)$ independently. The issue:
Poisson's *relative* variability (its **coefficient of variation squared**,
$\mathrm{Var}(X)/\mathbb{E}[X]^2 = 1/\lambda$) is **large when $\lambda$ is
small**. A big underdog with $\lambda_B \approx 0.92$ has
$\mathrm{Var}(X_B)/\mathbb{E}[X_B]^2 = 1/0.92 \approx 1.09$ — its
standard deviation is *larger than its own mean*. Concretely, for
$\lambda = 0.92$:

$$
P(X \ge 5) \approx 0.00257 \quad\Big(\approx \tfrac{1}{389}\Big)
$$

— not enormous in isolation, but across **2,000 simulated tournaments × dozens
of matches per tournament**, "the huge underdog scores 5 goals against a
title favorite" fluke results showed up often enough to look like a *model
bug* rather than a rare event — in one frozen example, a small Pacific nation
beat a much stronger team 5–2 in the displayed (fixed-seed) group table,
purely because Poisson's tail for small $\lambda$ is proportionally heavy.

### 5.2 The chosen alternative: the Binomial distribution

The model instead draws goals as the number of "successes" out of a fixed
number of independent trials:

$$
X \sim \mathrm{Binomial}(n, p), \qquad P(X=k) = \binom{n}{k} p^k (1-p)^{n-k}
$$

with $n = 6$ ("scoring chances," $\texttt{SCORING\_CHANCES}$, set equal to
$\lambda_{\max}$) and $p = \lambda / n$.

**Interpretation:** model a match as **6 discrete scoring chances**, each
independently converted into a goal with probability $p = \lambda/6$. This
maps onto a real concept in football analytics — *expected goals per shot /
per chance* — treating the match as a fixed number of "meaningful attacking
opportunities," each succeeding or failing independently.

#### 5.2.1 Why this fixes the problem — a direct variance comparison

By construction:

$$
\mathbb{E}[X] = np = 6 \cdot \frac{\lambda}{6} = \lambda \quad\text{— exactly the same mean as the Poisson model.}
$$

$$
\mathrm{Var}(X) = np(1-p) = \lambda\left(1 - \frac{\lambda}{6}\right) < \lambda \quad\text{for all } \lambda \in (0,6)
$$

**The Binomial model has the *same average outcome* as the Poisson model,
but strictly lower variance** — the $(1-\lambda/6)$ factor is always less
than 1. The reduction is most dramatic for *small* $\lambda$ — exactly the
big-underdog case that was producing fluke blowouts.

| $\lambda$ | $\mathrm{Var}(\mathrm{Poisson}(\lambda)) = \lambda$ | $\mathrm{Var}(\mathrm{Binomial}(6,\lambda/6)) = \lambda(1-\lambda/6)$ |
|---|---|---|
| $0.5$ | $0.500$ | $0.458$ |
| $1.0$ | $1.000$ | $0.833$ |
| $2.0$ | $2.000$ | $1.333$ |
| $3.0$ | $3.000$ | $1.500$ |
| $4.0$ | $4.000$ | $1.333$ |
| $5.0$ | $5.000$ | $0.833$ |
| $6.0$ | $6.000$ | $0.000$ |

At $\lambda = 6$, $p=1$ and the Binomial distribution becomes **degenerate**
(certain to produce exactly 6) — the variance correctly goes to zero, since
"6 out of 6 chances convert" leaves no room for randomness. The Poisson model
has no such ceiling and would assign positive probability to, say, $X=20$,
however vanishingly small.

For the concrete underdog case from §5.1.1 ($\lambda \approx 0.92$, so
$p = 0.92/6 \approx 0.1533$):

$$
P_{\text{Poisson}}(X \ge 5) \approx 0.00257 \quad\big(\approx 1/389\big) \qquad\text{vs.}\qquad P_{\text{Binomial}(6,p)}(X \ge 5) \approx 0.00044 \quad\big(\approx 1/2254\big)
$$

— roughly a **5.8× reduction** in the probability of a 5+ goal "blowout"
performance by a heavy underdog, while leaving the *expected* scoreline
completely unchanged.

#### 5.2.2 Bounded support — the other key property

$\mathrm{Binomial}(6, p)$ has support $\{0, 1, \dots, 6\}$ — it is
**structurally impossible** to sample more than 6 goals, which dovetails
exactly with the $\lambda_{\max}=6$ cap from §4.2.3: the maximum *expected*
goals and the maximum *possible* goals are the same number, by design.

### 5.3 The Poisson limit theorem — how the two distributions relate

It's worth noting that Binomial and Poisson are not unrelated models plucked
from different families — they are connected by one of the most famous
limit theorems in probability. If $n \to \infty$ and $p \to 0$ such that
$np = \lambda$ stays fixed, then:

$$
\mathrm{Binomial}(n, p) \xrightarrow{d} \mathrm{Poisson}(\lambda)
$$

(convergence in distribution — this is the **law of rare events** /
**Poisson limit theorem**, the same principle that originally justifies using
Poisson for "goals in a match" at all, as the limit of many independent
low-probability scoring opportunities). So $\mathrm{Binomial}(6, \lambda/6)$
can be understood as a **finite-$n$ approximation to $\mathrm{Poisson}(\lambda)$
with $n=6$** — close enough to share the same mean and overall shape, but
*deliberately* stopping short of the $n\to\infty$ limit specifically to retain
the lower variance and bounded support that make it more realistic for a
single football match (where there genuinely are only a handful of clear
scoring chances, not an unbounded number of infinitesimally-likely ones).

**Suggested Figure 5.1** — side-by-side bar charts (PMFs) of
$\mathrm{Poisson}(\lambda)$ vs. $\mathrm{Binomial}(6, \lambda/6)$ for a few
values of $\lambda$ (e.g. $0.92$, $2.0$, $4.0$) — same mean, visibly different
tails (Binomial cuts off at 6 and has less mass in the far right tail for
small $\lambda$).

**Suggested Figure 5.2** — the variance-comparison table above, plotted as
two curves $\mathrm{Var}(\lambda)$ vs. $\lambda \in [0,6]$ — a straight line
($y=\lambda$) for Poisson and a downward parabola
($y = \lambda - \lambda^2/6$) for Binomial, meeting only at the endpoints
$\lambda=0$ and $\lambda=6$.

**Suggested Figure 5.3** (optional, more advanced) — illustrate the Poisson
limit theorem itself: for a fixed $\lambda$ (say $2.0$), overlay
$\mathrm{Binomial}(n, \lambda/n)$ PMFs for increasing $n \in \{6, 20, 100,
1000\}$ alongside $\mathrm{Poisson}(2.0)$, showing visual convergence.

### 5.4 Independence assumption (a noted simplification)

$X_A$ and $X_B$ are sampled **independently**. In reality, match dynamics
introduce some negative correlation (e.g., a team leading late tends to
"sit back," suppressing further goals from both sides) — addressed in the
literature by models like Dixon–Coles (1997), which add a small correlation
adjustment $\tau$ specifically for low-scoring outcomes. This model omits
that adjustment for simplicity and tractability; it is a known, deliberate
simplification rather than an oversight, and would be a natural extension.

---

## 6. Two modes of simulating a single match

The model produces **two different kinds of output** from the same
$(\lambda_A, \lambda_B)$ pair, depending on whether the goal is a
*probability distribution over outcomes* or a *single representative
scenario*:

### 6.1 Stochastic mode — for Monte Carlo simulation (§9)

$X_A \sim \mathrm{Binomial}(6, \lambda_A/6)$ and
$X_B \sim \mathrm{Binomial}(6, \lambda_B/6)$, drawn independently using a
pseudo-random number generator. This is what's used inside the **2,000-trial**
loop that estimates championship probabilities.

### 6.2 Deterministic mode — for the displayed "representative" tournament

$$
\hat{X}_A = \left\lfloor \lambda_A + \tfrac12 \right\rfloor, \qquad \hat{X}_B = \left\lfloor \lambda_B + \tfrac12 \right\rfloor
$$

i.e., **round the expected goals to the nearest integer**, with no
randomness at all. The same Power Score inputs always produce the same
scoreline.

**A subtlety worth noting for a mathematically-minded reader:** rounding the
*mean* $\lambda$ is a simple, interpretable proxy for "the single most
representative outcome," but it is not identical to the **mode** (most
probable single value) of the underlying distribution. For
$\mathrm{Binomial}(n,p)$, the mode is $\lfloor (n+1)p \rfloor$ (generically),
which can differ from $\lfloor \lambda + 1/2 \rfloor = \lfloor np + 1/2
\rfloor$ by one in some cases. The model uses "round the mean" deliberately
for its simplicity and its direct, transparent connection to the
$\lambda$ formula from §4.2 — "what the formula literally predicts," rather
than a separate most-likely-scoreline calculation.

### 6.3 Tie-breaking

- **Group stage** (deterministic mode): if $\hat{X}_A = \hat{X}_B$, this is
  recorded as a genuine **draw** — group standings have real draws, just as
  real World Cup groups do.
- **Knockout stage, stochastic mode**: a tie after 90+30 minutes goes to a
  **penalty shootout**, resolved via the logistic win-probability model from
  §4.1: $\mathrm{Bernoulli}(P(A \text{ beats } B))$ decides the winner, and
  the shootout score itself is generated as
  $\text{winner's penalties} \sim \mathrm{Uniform}\{3,4,5\}$ and
  $\text{loser's penalties} \sim \mathrm{Uniform}\{0, \dots, \text{winner's
  penalties} - 1\}$ — a stylistic detail (penalty shootouts have no
  "expected score" formula in the way open play does) included for display
  realism.
- **Knockout stage, deterministic mode**: a tie after rounding is broken by
  simply comparing the underlying *continuous* Power Scores directly —
  $S_A \ge S_B \Rightarrow A$ advances. This is a **lexicographic
  refinement**: the discretized goal count is the primary sort key, and the
  un-rounded Power Score (which "remembers" arbitrarily small differences
  the rounding discarded) is the tiebreaker. A fixed $4$–$3$ penalty score is
  displayed for cosmetic consistency (there being no formula for a shootout
  score in the deterministic, no-randomness setting).

---

## 7. The tournament as a combinatorial object

Before discussing Monte Carlo aggregation, it's worth pausing on the
**combinatorial structure** being simulated — this is what makes "simulate
the tournament" a non-trivial computation rather than just "simulate one
match."

### 7.1 Group stage: round-robin

The 48 teams are partitioned into **12 groups of 4**. Within each group,
every pair of teams plays exactly once — a **complete graph $K_4$** on the
group's 4 teams, i.e.

$$
\binom{4}{2} = 6 \text{ matches per group}, \qquad 12 \times 6 = 72 \text{ group-stage matches total.}
$$

### 7.2 Standings and the tiebreak ordering

After the round-robin, each team has accumulated points
($3$ for a win, $1$ for a draw, $0$ for a loss), goals for, and goals
against. Teams within a group are ranked by the **lexicographic order** on
the tuple:

$$
\big(-\text{points},\ -\text{goal difference},\ -\text{goals for},\ -S_i\big)
$$

(negated so that "sort ascending" = "rank from best to worst"). Lexicographic
order means: compare points first; only if *equal*, compare goal difference;
only if *still equal*, compare goals for; only if *still equal*, fall back to
the continuous Power Score $S_i$ as a final tiebreaker (which — being a real
number computed from 11 weighted features — is essentially never exactly
tied between two different teams, so this guarantees a strict total order
with no remaining ambiguity).

### 7.3 Qualification and the "next power of two"

The top 2 teams from each of the 12 groups qualify directly:
$12 \times 2 = 24$ teams. A single-elimination knockout bracket with $r$
rounds requires exactly $2^r$ entrants. Since $24$ is not a power of two, the
**best 8 third-place teams** (by the same lexicographic ordering as §7.2,
computed across all 12 third-placed teams) are added to bring the bracket up
to:

$$
24 + 8 = 32 = 2^5
$$

giving exactly $r=5$ knockout rounds: Round of 32, Round of 16, Quarterfinals,
Semifinals, Final. In general, the model computes
$\text{target\_size} = 2^{\lceil \log_2(|\text{direct qualifiers}|)\rceil}$
(the **next power of two**) and fills the gap with the best remaining
third-placed teams — a general mechanism that works for any group/qualifier
configuration, not just the specific 12×4 World Cup shape.

### 7.4 Bracket seeding as constrained random assignment

The 32 qualifiers are split into two **bracket halves** of 16, and within
each half, paired up into 8 first-round matches. Two constraints are applied:

1. **Group-mates are kept apart** — two teams that played each other in the
   group stage are prevented from meeting again until the Final (mirroring
   real-world tournament seeding rules). This is essentially a
   **graph-coloring / derangement-style constraint**: build the assignment so
   that no early-round pair shares a "group" label.
2. Subject to constraint 1, the assignment is otherwise a **random
   permutation** (a simulated "draw"), generated by a seeded random number
   generator (so it is reproducible for a given seed but otherwise looks like
   a genuine lottery draw).

### 7.5 The knockout bracket as a binary tree

A single-elimination bracket with $N = 2^r$ entrants is a **complete binary
tree of depth $r$**, with $N-1$ internal nodes (matches):

$$
N - 1 = 2^r - 1
$$

For $N=32$: $31$ knockout matches across the 5 rounds
($16 + 8 + 4 + 2 + 1 = 31$). Each match's winner advances to the parent node;
the root of the tree is the Final, and its winner is the champion.

**Suggested Figure 7.1** — a literal binary-tree diagram of the 32-team
bracket: 5 columns (Round of 32 → Final), with connector lines from each
match to the match it feeds into — both as a combinatorics illustration
($31 = 2^5-1$ nodes) and as a template for the actual results display.

---

## 8. The deterministic "representative" tournament

A single pass through the entire tournament structure (§7), using the
**deterministic** match function from §6.2 throughout (rounded expected
goals, lexicographic tiebreaks, no randomness in scorelines), produces one
specific, fully reproducible group stage and bracket. The *only* randomness
involved is in the bracket **draw** (§7.4) — which qualifiers land in which
half/match — using a separately-seeded random number generator that affects
*pairings* only, never *scores*.

This is conceptually a **point estimate / point forecast**: "given these
weights, here is the single scenario the formula considers most
representative of the mean outcome at every step." It is intentionally kept
separate from the genuinely probabilistic quantity computed in §9 — the two
serve different purposes:

| | Representative tournament (§8) | Champion probabilities (§9) |
|---|---|---|
| Randomness in match scores | None (rounded means) | Yes (Binomial draws) |
| Reproducibility | Always identical for given weights | Always identical for given weights *and seed* |
| Interpretation | "What the formula predicts will happen" | "How often team $i$ wins across many possible tournaments" |
| Statistical nature | A single point estimate | An estimated probability distribution |

This mirrors a standard distinction in forecasting: a **point forecast**
(a single number/scenario) vs. a **probabilistic forecast** (a distribution
over possible outcomes) — both useful, answering different questions.

---

## 9. Stage 5 — Monte Carlo simulation of championship probabilities

### 9.1 The estimator

For $T = 2{,}000$ independent trials, the *entire* tournament (§7) is played
out in **stochastic mode** (§6.1, with $X_A, X_B \sim \mathrm{Binomial}(6,
\cdot)$ at every match, including a fresh random bracket draw each trial),
producing a champion $c_t \in \{1, \dots, 48\}$ for trial $t$.

For each team $i$, the **champion probability** is estimated as the sample
proportion:

$$
\hat{p}_i = \frac{1}{T}\sum_{t=1}^{T} \mathbb{1}[c_t = i]
$$

i.e., simply *count how often team $i$ wins across $2{,}000$ replayed
tournaments, divide by $2{,}000$.*

### 9.2 Why this works: the Law of Large Numbers

Each indicator $\mathbb{1}[c_t = i]$ is a Bernoulli random variable with
(unknown) true success probability $p_i$ — "the probability that team $i$
wins the tournament, given this round's random draws of every match
throughout the bracket." By the (weak) **Law of Large Numbers**:

$$
\hat{p}_i \xrightarrow{P} p_i \quad \text{as } T \to \infty
$$

The sample proportion converges in probability to the true probability — this
is the entire theoretical justification for "running the simulation many
times and counting." Monte Carlo simulation is, at its core, just an
application of the Law of Large Numbers to a process too complex to solve in
closed form (a 48-team, 103-match knockout-plus-group tournament has far too
much combinatorial structure for $p_i$ to be computed analytically).

### 9.3 Precision: standard error of the estimate

Since $\sum_{t=1}^T \mathbb{1}[c_t=i] \sim \mathrm{Binomial}(T, p_i)$, the
standard error of $\hat{p}_i$ is:

$$
\mathrm{SE}(\hat{p}_i) = \sqrt{\frac{\hat{p}_i(1-\hat{p}_i)}{T}}
$$

For a **leading contender** with $\hat{p}_i \approx 0.41$ (e.g. a tournament
favorite) and $T=2000$:

$$
\mathrm{SE} \approx \sqrt{\frac{0.41 \times 0.59}{2000}} \approx 0.011
$$

— i.e. the headline "41%" is precise to roughly **±1.1 percentage points**
(one standard error) — quite tight.

For a **rare contender** with $\hat{p}_i \approx 0.005$ (a 0.5% outsider):

$$
\mathrm{SE} \approx \sqrt{\frac{0.005 \times 0.995}{2000}} \approx 0.0016
$$

The *absolute* error (±0.16 percentage points) is small, but the **relative**
error $\mathrm{SE}/\hat{p}_i \approx 32\%$ is large — rare-event probabilities
are estimated far less precisely by a fixed-$T$ Monte Carlo simulation than
common-event probabilities. This is the classic **Monte Carlo rare-event
problem**: a "1-in-200 chance" team might genuinely have a true probability
anywhere from roughly 1-in-300 to 1-in-140 given only 2,000 trials. (Standard
mitigations — importance sampling, stratified sampling — exist in the Monte
Carlo literature but are not implemented here; noted as a natural extension.)

### 9.4 Reproducibility via seeding

The pseudo-random number generator is seeded with a fixed value
($\texttt{seed}=42$). A PRNG is a **deterministic function of its seed and
call sequence** — "randomness" here means "looks statistically random and is
extremely hard to predict without running the algorithm," not "different
every time." Fixing the seed means: **the same weight configuration always
produces the exact same champion-probability distribution.** This is a
deliberate product property — "your formula → your results," reproducible
and auditable — not a limitation. A different seed would produce slightly
different $\hat{p}_i$ values (within the standard-error bounds of §9.3), but
the same underlying true distribution.

**Suggested Figure 9.1** — a "Monte Carlo convergence" plot: x-axis = number
of trials $T$ (from 1 to 2000, or beyond), y-axis = running estimate
$\hat{p}_i(T) = \frac{1}{T}\sum_{t\le T}\mathbb{1}[c_t=i]$ for 2–3 example
teams, showing the estimates fluctuating wildly for small $T$ and settling
down toward stable values as $T$ grows — a direct visualization of the Law of
Large Numbers in action. (This can be generated by re-running the simulation
with increasing trial counts and plotting the cumulative champion frequency.)

**Suggested Figure 9.2** — the final output: a horizontal bar chart of
$\hat{p}_i$ for the top ~10 teams by championship probability, each bar
optionally annotated with its $\pm 1$ SE error bar from §9.3 — turning the
"Champion %" leaderboard into a statistically-honest plot with uncertainty
shown explicitly.

---

## 10. Putting it all together — a worked end-to-end example

To tie every section together, trace one concrete pair of teams through the
*entire* pipeline (using the population-factor example from §2.3, with all
other weights set to zero so the effect is isolated — "solo mode"):

1. **§2.3 Normalization**: Germany's population (≈83.5M) and Curaçao's
   population (≈156K) are log-normalized to $f^{\text{pop}}_{\text{GER}} =
   0.817$ and $f^{\text{pop}}_{\text{CUW}} = 0.000$.
2. **§3.2 Power Score**: with population the *only* nonzero weight
   ($w_{\text{pop}}=1$, all others $0$), $S_{\text{GER}} = 0.817$ and
   $S_{\text{CUW}} = 0.000$.
3. **§4.1 Win probability**: $\Delta = 0.817$, giving
   $P(\text{GER beats CUW}) \approx 1.000$ (effectively certain).
4. **§4.2 Expected goals**: $\lambda_{\text{GER}} = \min(1.35 \cdot
   e^{2.2 \times 0.817}, 6) = 6.000$ (capped) and $\lambda_{\text{CUW}} =
   1.35 \cdot e^{-2.2\times 0.817} \approx 0.224$.
5. **§5.2 / §6.2 Goal sampling (deterministic mode)**:
   $\hat{X}_{\text{GER}} = \lfloor 6.000+0.5\rfloor = 6$,
   $\hat{X}_{\text{CUW}} = \lfloor 0.224+0.5\rfloor = 0$.
6. **Result**: **Germany 6 – 0 Curaçao** — a result that finally reflects the
   536× real-world population gap, after the log-normalization fix in §2.3
   (prior to that fix, the same scenario produced only a 2–1 scoreline,
   because the *linear* normalization of population compressed Germany's gap
   down to $\Delta=0.245$ instead of $0.817$).

This example demonstrates how a choice made all the way back in **Stage 1
(normalization)** propagates, through four further deterministic
transformations, all the way to the final scoreline — and why getting that
first choice right (log-scale vs. linear) mattered so much to the realism of
the final output.

---

## 11. Glossary of notation

| Symbol | Meaning |
|---|---|
| $i, j$ | Team indices, $i,j \in \{1,\dots,48\}$ |
| $k$ | Factor/feature index, $k \in \{1,\dots,11\}$ |
| $x_{i,k}$ | Raw value of factor $k$ for team $i$ |
| $f_{i,k} \in [0,1]$ | Normalized value of factor $k$ for team $i$ |
| $w_k$ | Normalized weight for factor $k$ ($\sum_k w_k = 1$, $w_k \ge 0$) |
| $S_i \in [0,1]$ | Power Score of team $i$ |
| $\Delta = S_A - S_B \in [-1,1]$ | Power Score gap between two teams |
| $K = 6.0$ | Logistic steepness constant |
| $G = 1.35$ | Baseline expected goals between equal teams |
| $\gamma = 2.2$ | Expected-goals scale constant |
| $\lambda_{\max} = 6.0$ | Cap on expected goals (= max possible goals) |
| $\lambda_A, \lambda_B$ | Expected goals for teams $A$, $B$ |
| $n = 6$ | Number of "scoring chances" (Binomial trials) |
| $p = \lambda/n$ | Per-chance conversion probability |
| $T = 2000$ | Number of Monte Carlo trials |
| $\hat{p}_i$ | Monte Carlo estimate of team $i$'s championship probability |

---

## 12. References / further reading

These are the established statistical/mathematical concepts this model draws
on — useful pointers for a reader who wants to go deeper into any one piece:

- **Elo, A. (1978).** *The Rating of Chessplayers, Past and Present.* — origin
  of the logistic expected-score formula used in §4.1.
- **Bradley, R. A., & Terry, M. E. (1952).** *Rank Analysis of Incomplete
  Block Designs* — the Bradley–Terry pairwise comparison model.
- **Maher, M. J. (1982).** *Modelling Association Football Scores* — the
  foundational log-linear (Poisson) goals model referenced in §4.2 and §5.1.
- **Dixon, M. J., & Coles, S. G. (1997).** *Modelling Association Football
  Scores and Inefficiencies in the Football Betting Market* — extends Maher's
  model with a low-score correlation adjustment (§5.4).
- **Weber–Fechner law** (psychophysics) — the perceptual basis for log-scale
  normalization (§2.3).
- **Poisson limit theorem / law of rare events** — the Binomial-to-Poisson
  convergence discussed in §5.3.
- **Law of Large Numbers** — the theoretical basis for Monte Carlo estimation
  (§9.2).
- **Simple Additive Weighting (SAW) / weighted-sum model** — the
  multi-criteria decision analysis technique underlying §3.

---

## Appendix: Full list of suggested figures

For convenience, all suggested figures from the document above, in order:

1. **Fig 1.1** — End-to-end pipeline flow diagram (§1).
2. **Fig 2.1** — Linear min-max as a "stretch and shift" of a number line (§2.2).
3. **Fig 2.2** — Linear vs. log-scale normalization of population, two-panel scatter (§2.3) — *highest priority figure*.
4. **Fig 2.3** — Inverted normalization as a reflection (§2.4).
5. **Fig 2.4** — Elo-vs-FIFA-points scatter with OLS regression line and imputed points (§2.7).
6. **Fig 3.1** — Stacked bar chart of one team's Power Score as a sum of weighted factors (§3.3).
7. **Fig 3.2** — Bar chart of all 48 teams' Power Scores, ranked (§3.3).
8. **Fig 4.1** — Logistic win-probability curve $P(\Delta)$ (§4.1).
9. **Fig 4.2** — Exponential expected-goals curves $\lambda_A(\Delta)$, $\lambda_B(\Delta)$ (§4.2).
10. **Fig 5.1** — Poisson vs. Binomial PMF bar charts at matching means (§5.3).
11. **Fig 5.2** — Variance curves: $\mathrm{Var}=\lambda$ (Poisson) vs. $\lambda(1-\lambda/6)$ (Binomial) (§5.3).
12. **Fig 5.3** (optional) — Binomial→Poisson convergence illustration (§5.3).
13. **Fig 7.1** — Binary-tree bracket diagram, 32 teams / 31 matches (§7.5).
14. **Fig 9.1** — Monte Carlo convergence plot, running champion-probability estimate vs. $T$ (§9.3).
15. **Fig 9.2** — Final champion-probability bar chart with standard-error bars (§9.3).
