# **Goalifai – Financial Tracking Module**

*A structured system for capturing and understanding personal financial behavior*

---

## **📘 Overview**

The Financial Tracking Module powers Goalifai’s ability to transform raw financial transactions into meaningful insights.
The system records **expenses**, then classifies them by:

* **Expense Intent** → *why* the expense happened
* **Expense Beneficiary** → *who* the expense benefits

These two foundations will power future analytics, decision support, budgeting, and personalized goal recommendations.

---

# **✔️ Achieved Implementations**

## **### 1. Expense Intent (New)**

The **reason** behind a financial transaction.

**Supported Intents:**

| Intent                        | Description                                                            |
| ------------------------------|------------------------------------------------------------------------|
| **Need (Essentials)**         | Essential survival or required daily living expenses.                  |
| **Want (lifestyle wants)**    | Non-essential, lifestyle, enjoyment, or comfort purchases.             |
| **Obligation**                | Social or family duties (cultural, moral, or relationship-based).      |
| **Investment**                | Spending that improves future value (skills, assets, personal growth). |
| **Maintenance**               | Upkeep of possessions, services, or well-being.                        |
| **Income-Generating**         | Any spending related to earning income or productivity.                |
| **Social Contribution**       | Donations, gifts, community support, helping others.                   |

**Examples:**

* Buying a suit for a job → Investment / Need
* Buying a fashion suit → Want
* Bus fare to attend a family wedding → Obligation
* Spotify subscription → Want / Entertainment

---

## **### 2. Expense Beneficiary (New)**

Defines **who benefits** from the expense.

**Supported Beneficiaries:**

| Beneficiary   | Description                                     |
| ------------- | ----------------------------------------------- |
| **Self**      | Directly benefits the user.                     |
| **Family**    | Parents, siblings, extended family.             |
| **Friends**   | Social relationships, friendships.              |
| **Partner**   | Romantic partner/spouse.                        |
| **Children**  | Biological, adopted, dependents.                |
| **Community** | Society, charity, church, public contributions. |
| **Employer/work**      | Employer-related or job-related spending.       |

**Examples:**

* Spotify subscription → Self
* Buying food for family → Family
* Gift for a friend’s wedding → Friend
* Church tithe → Community

---

# **🚧 Next Steps (Planned Implementations)**

## **1. Category & Subcategory System**

Implement the top-level structure for:

* Food, Housing, Transport, Entertainment, Essentials, etc.
  Then define deeper subcategories.

## **2. Classification Engine**

Combine **Intent + Beneficiary + Category** to produce:

* Insights
* Financial patterns
* Behavioral scoring

## **3. Recurring Expense Detection**

Detect subscriptions like:

* Spotify
* Netflix
* Internet
* Rent

Mark them as recurring and predict future obligations.

## **4. Dashboard for Financial Insights**

Introduce:

* Wants vs Needs ratio
* Self vs Others spending balance
* Monthly obligation tracking
* Social contribution analytics

## **5. Integration With Goal System**

Link expenses to:

* Goals
* Savings
* Required spending
* Cost projections

## **6. Machine Learning Auto-Classification**

Later stage:

* Predict intent
* Predict beneficiary
* Predict category
* Improve automatically over time

## **7. Receipt OCR & Bulk Import**

Use camera capture or uploads to auto-extract:

* Amount
* Category
* Intent suggestions

## **8. Alerts & Smart Recommendations**

Examples:

* “Your wants exceeded your budget this month.”
* “You spent more on others than yourself this week.”
* “Your obligations have increased compared to last month.”

---

# **🎯 Vision**

Goalifai aims to build a financial system that **understands behavior**, not just transactions—helping users grow, align spending with goals, and make better life decisions.

---
