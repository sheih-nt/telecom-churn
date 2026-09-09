from flask import Flask, render_template, request, jsonify
import pandas as pd

app = Flask(__name__)

df = pd.read_csv("data/data.csv", sep=";", decimal=",")

df.columns = df.columns.str.strip()

for column in [
    "Monthly Charges",
    "Total Charges",
    "CLTV",
    "Churn Value",
    "Tenure Months"
]:
    df[column] = pd.to_numeric(
        df[column].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    )

df["Churn Value"] = df["Churn Value"].fillna(0).astype(int)


def tenure_group(value):
    if value <= 3:
        return "0-3"
    if value <= 6:
        return "4-6"
    if value <= 12:
        return "7-12"
    if value <= 24:
        return "13-24"
    if value <= 48:
        return "25-48"
    return "49-72"


df["Tenure Group"] = df["Tenure Months"].apply(tenure_group)


def get_kpi(data):
    customers = len(data)
    churned = int(data["Churn Value"].sum())

    if customers:
        churn_rate = churned / customers * 100
        avg_monthly = data["Monthly Charges"].mean()
        avg_cltv = data["CLTV"].mean()
    else:
        churn_rate = 0
        avg_monthly = 0
        avg_cltv = 0

    return {
        "customers": customers,
        "churned": churned,
        "churn_rate": round(churn_rate, 2),
        "mrr": round(data["Monthly Charges"].sum(), 2),
        "avg_monthly": round(avg_monthly, 2),
        "avg_cltv": round(avg_cltv, 2)
    }


def get_chart_data(data, column):
    result = (
        data
        .groupby(column)
        .agg(
            customers=("CustomerID", "count"),
            churned=("Churn Value", "sum")
        )
        .reset_index()
    )

    result["churn_rate"] = (
        result["churned"] /
        result["customers"] *
        100
    ).round(2)

    return result.to_dict("records")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/options")
def options():
    return jsonify({
        "contract": sorted(
            df["Contract"].dropna().unique().tolist()
        ),
        "internet": sorted(
            df["Internet Service"].dropna().unique().tolist()
        ),
        "tenure": [
            "0-3",
            "4-6",
            "7-12",
            "13-24",
            "25-48",
            "49-72"
        ],
        "payment": sorted(
            df["Payment Method"].dropna().unique().tolist()
        )
    })


@app.route("/api/dashboard")
def dashboard():
    data = df.copy()

    contract = request.args.get("contract")
    internet = request.args.get("internet")
    tenure = request.args.get("tenure")
    payment = request.args.get("payment")

    if contract:
        data = data[data["Contract"] == contract]

    if internet:
        data = data[data["Internet Service"] == internet]

    if tenure:
        data = data[data["Tenure Group"] == tenure]

    if payment:
        data = data[data["Payment Method"] == payment]

    reasons = (
        data[data["Churn Value"] == 1]
        .groupby("Churn Reason")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="count")
        .to_dict("records")
    )

    priority = data[
        (data["Contract"] == "Month-to-month") &
        (data["Internet Service"] == "Fiber optic")
    ]

    return jsonify({
        "kpi": get_kpi(data),

        "contract": get_chart_data(
            data,
            "Contract"
        ),

        "internet": get_chart_data(
            data,
            "Internet Service"
        ),

        "tenure": get_chart_data(
            data,
            "Tenure Group"
        ),

        "payment": get_chart_data(
            data,
            "Payment Method"
        ),

        "reasons": reasons,

        "priority": get_kpi(priority)
    })


if __name__ == "__main__":
    app.run(debug=True)