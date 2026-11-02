#!/usr/bin/env python3
"""Midterm Data Science Analysis: South German Credit."""

from pathlib import Path
import io
import json
import zipfile

import joblib
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "static" / "analysis"
MODEL_DIR = BASE_DIR / "models"
REPORT_DIR = BASE_DIR / "report"

DATA_FILE = DATA_DIR / "south_german_credit.csv"
CLEAN_DATA_FILE = DATA_DIR / "south_german_credit_cleaned.csv"
RESULTS_FILE = OUTPUT_DIR / "analysis_results.json"

UCI_DATASET_ID = 573
UCI_DATASET_PAGE = (
    "https://archive.ics.uci.edu/dataset/573/south+german+credit"
)
UCI_DATASET_ZIP = (
    "https://archive.ics.uci.edu/static/public/573/"
    "south+german+credit.zip"
)
UCI_DOI = "https://doi.org/10.24432/C5QG88"

COLUMN_RENAME = {
    "laufkont": "status",
    "laufzeit": "duration",
    "moral": "credit_history",
    "verw": "purpose",
    "hoehe": "amount",
    "sparkont": "savings",
    "beszeit": "employment_duration",
    "rate": "installment_rate",
    "famges": "personal_status_sex",
    "buerge": "other_debtors",
    "wohnzeit": "present_residence",
    "verm": "property",
    "alter": "age",
    "weitkred": "other_installment_plans",
    "wohn": "housing",
    "bishkred": "number_credits",
    "beruf": "job",
    "pers": "people_liable",
    "telef": "telephone",
    "gastarb": "foreign_worker",
    "kredit": "credit_risk",
}

CATEGORICAL_COLUMNS = [
    "status",
    "credit_history",
    "purpose",
    "savings",
    "personal_status_sex",
    "other_debtors",
    "property",
    "other_installment_plans",
    "housing",
    "job",
    "telephone",
    "foreign_worker",
    "age_group",
]

NUMERIC_COLUMNS = [
    "duration",
    "amount",
    "employment_duration",
    "installment_rate",
    "present_residence",
    "age",
    "number_credits",
    "people_liable",
    "amount_per_month",
]


def acquire_dataset():
    """
    Load the South German Credit dataset.

    If a local CSV already exists, use it. Otherwise, download the official
    UCI ZIP archive directly and save a local CSV copy for reproducibility.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if DATA_FILE.exists():
        print(f"Loading local dataset: {DATA_FILE}")
        return pd.read_csv(DATA_FILE)

    print("Downloading South German Credit directly from UCI...")

    response = requests.get(UCI_DATASET_ZIP, timeout=60)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        file_name = "SouthGermanCredit.asc"

        if file_name not in archive.namelist():
            raise FileNotFoundError(
                f"{file_name} was not found in the UCI ZIP archive."
            )

        with archive.open(file_name) as file:
            df = pd.read_csv(
                file,
                sep=r"\s+",
                engine="python",
                header=0,
            )

    print(
        f"Dataset downloaded: {df.shape[0]} rows, "
        f"{df.shape[1]} columns"
    )

    df.to_csv(DATA_FILE, index=False)
    print(f"Saved local copy: {DATA_FILE}")

    return df


def clean_dataset(df):
    """
    Clean the dataset by:
    - renaming columns
    - removing duplicates
    - converting numeric columns
    - filling missing predictor values
    - removing invalid records
    - converting the original target to 0=good, 1=bad for easier evaluation

    Important:
    The source dataset codes credit_risk as:
        0 = bad
        1 = good

    For this project we reverse it to:
        0 = good
        1 = bad
    so precision/recall/F1 describe bad-risk detection.
    """
    df = df.rename(columns=COLUMN_RENAME).copy()

    starting_rows = len(df)
    duplicate_rows = int(df.duplicated().sum())
    missing_before = int(df.isnull().sum().sum())

    df = df.drop_duplicates().copy()

    numeric_candidates = [
        "duration",
        "amount",
        "employment_duration",
        "installment_rate",
        "present_residence",
        "age",
        "number_credits",
        "people_liable",
        "credit_risk",
    ]

    for column in numeric_candidates:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    for column in df.columns:
        if column == "credit_risk":
            continue

        if pd.api.types.is_numeric_dtype(df[column]):
            df[column] = df[column].fillna(
                df[column].median()
            )
        else:
            mode = df[column].mode(dropna=True)
            replacement = (
                mode.iloc[0]
                if not mode.empty
                else "Unknown"
            )
            df[column] = df[column].fillna(replacement)

    df = df.dropna(subset=["credit_risk"]).copy()

    invalid_mask = (
        (df["duration"] <= 0)
        | (df["amount"] <= 0)
        | (df["age"] < 18)
        | (df["age"] > 100)
        | (~df["credit_risk"].isin([0, 1]))
    )

    invalid_rows = int(invalid_mask.sum())
    df = df.loc[~invalid_mask].copy()

    # UCI source: 0 = bad, 1 = good.
    # Project convention: 0 = good, 1 = bad.
    df["credit_risk"] = (
        1 - df["credit_risk"].astype(int)
    )

    return df, {
        "starting_rows": starting_rows,
        "duplicate_rows_removed": duplicate_rows,
        "missing_cells_before_cleaning": missing_before,
        "invalid_rows_removed": invalid_rows,
        "final_rows": len(df),
        "missing_cells_after_cleaning": int(
            df.isnull().sum().sum()
        ),
    }


def engineer_features(df):
    """Create two additional features for preprocessing/modeling."""
    df = df.copy()

    df["amount_per_month"] = (
        df["amount"] / df["duration"]
    )

    df["age_group"] = pd.cut(
        df["age"],
        bins=[17, 25, 35, 50, 65, 100],
        labels=[
            "18-25",
            "26-35",
            "36-50",
            "51-65",
            "66+",
        ],
        include_lowest=True,
    ).astype(str)

    return df


def build_preprocessor():
    """
    Build preprocessing pipelines.

    Numeric:
    - median imputation
    - standard scaling

    Categorical:
    - most-frequent imputation
    - one-hot encoding
    """
    numeric_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )

    return ColumnTransformer(
        [
            (
                "numeric",
                numeric_pipeline,
                NUMERIC_COLUMNS,
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_COLUMNS,
            ),
        ]
    )


def create_eda(df):
    """Run exploratory analysis and save visualizations."""
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nDataset info:")
    df.info()

    print("\nDescriptive statistics:")
    print(
        df.describe(
            include="all"
        ).transpose()
    )

    numeric = df.select_dtypes(
        include=np.number
    )

    stats = {
        "mean": numeric.mean().round(2).to_dict(),
        "median": (
            numeric.median()
            .round(2)
            .to_dict()
        ),
        "std": numeric.std().round(2).to_dict(),
    }

    # 1. Histogram
    plt.figure(figsize=(8, 5))
    plt.hist(
        df["amount"],
        bins=30,
        edgecolor="black",
    )
    plt.title(
        "Distribution of Credit Amount"
    )
    plt.xlabel("Credit amount")
    plt.ylabel("Number of records")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "amount_histogram.png",
        dpi=150,
    )
    plt.close()

    # 2. Boxplot
    good_duration = df.loc[
        df["credit_risk"] == 0,
        "duration",
    ]
    bad_duration = df.loc[
        df["credit_risk"] == 1,
        "duration",
    ]

    plt.figure(figsize=(8, 5))
    plt.boxplot(
        [good_duration, bad_duration],
        tick_labels=[
            "Good risk",
            "Bad risk",
        ],
    )
    plt.title(
        "Credit Duration by Risk Outcome"
    )
    plt.xlabel("Credit risk")
    plt.ylabel("Duration (months)")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "duration_boxplot.png",
        dpi=150,
    )
    plt.close()

    # 3. Correlation heatmap
    corr_cols = [
        "duration",
        "amount",
        "installment_rate",
        "age",
        "number_credits",
        "amount_per_month",
        "credit_risk",
    ]

    correlation = df[corr_cols].corr()

    plt.figure(figsize=(9, 7))
    image = plt.imshow(
        correlation,
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
    )
    plt.colorbar(image)

    plt.xticks(
        range(len(corr_cols)),
        corr_cols,
        rotation=45,
        ha="right",
    )
    plt.yticks(
        range(len(corr_cols)),
        corr_cols,
    )

    for row in range(len(corr_cols)):
        for col in range(len(corr_cols)):
            plt.text(
                col,
                row,
                f"{correlation.iloc[row, col]:.2f}",
                ha="center",
                va="center",
                fontsize=8,
            )

    plt.title("Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR
        / "correlation_heatmap.png",
        dpi=150,
    )
    plt.close()

    # 4. Class-balance bar chart
    counts = (
        df["credit_risk"]
        .value_counts()
        .sort_index()
    )

    plt.figure(figsize=(7, 5))
    plt.bar(
        ["Good risk", "Bad risk"],
        [
            counts.get(0, 0),
            counts.get(1, 0),
        ],
    )
    plt.title("Credit Risk Class Balance")
    plt.xlabel("Credit risk")
    plt.ylabel("Number of records")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "class_balance.png",
        dpi=150,
    )
    plt.close()

    return (
        stats,
        correlation.round(3).to_dict(),
        counts.to_dict(),
    )


def evaluate_model(
    name,
    model,
    X_test,
    y_test,
):
    """Evaluate one classification model."""
    predictions = model.predict(X_test)

    metrics = {
        "accuracy": round(
            float(
                accuracy_score(
                    y_test,
                    predictions,
                )
            ),
            4,
        ),
        "precision": round(
            float(
                precision_score(
                    y_test,
                    predictions,
                    zero_division=0,
                )
            ),
            4,
        ),
        "recall": round(
            float(
                recall_score(
                    y_test,
                    predictions,
                    zero_division=0,
                )
            ),
            4,
        ),
        "f1": round(
            float(
                f1_score(
                    y_test,
                    predictions,
                    zero_division=0,
                )
            ),
            4,
        ),
        "confusion_matrix": confusion_matrix(
            y_test,
            predictions,
        ).tolist(),
        "classification_report": (
            classification_report(
                y_test,
                predictions,
                target_names=[
                    "Good risk",
                    "Bad risk",
                ],
                zero_division=0,
            )
        ),
    }

    print(
        f"\n{name}\n"
        f"{'-' * len(name)}"
    )
    print(
        metrics[
            "classification_report"
        ]
    )

    return metrics


def train_models(df):
    """Train and evaluate Logistic Regression and Random Forest."""
    X = df[
        NUMERIC_COLUMNS
        + CATEGORICAL_COLUMNS
    ].copy()

    y = df["credit_risk"].copy()

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    logistic = Pipeline(
        [
            (
                "preprocess",
                build_preprocessor(),
            ),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    forest = Pipeline(
        [
            (
                "preprocess",
                build_preprocessor(),
            ),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=200,
                    random_state=42,
                    class_weight="balanced",
                ),
            ),
        ]
    )

    logistic.fit(
        X_train,
        y_train,
    )

    forest.fit(
        X_train,
        y_train,
    )

    log_metrics = evaluate_model(
        "Logistic Regression",
        logistic,
        X_test,
        y_test,
    )

    rf_metrics = evaluate_model(
        "Random Forest",
        forest,
        X_test,
        y_test,
    )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        logistic,
        MODEL_DIR
        / "logistic_regression.joblib",
    )

    joblib.dump(
        forest,
        MODEL_DIR
        / "random_forest.joblib",
    )

    preprocessor = (
        forest.named_steps["preprocess"]
    )

    feature_names = (
        preprocessor.get_feature_names_out()
    )

    importances = (
        forest.named_steps[
            "model"
        ].feature_importances_
    )

    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": importances,
        }
    ).sort_values(
        "importance",
        ascending=False,
    )

    top_features = importance_df.head(12)

    plt.figure(figsize=(9, 6))
    ordered = top_features.iloc[::-1]

    plt.barh(
        ordered["feature"],
        ordered["importance"],
    )

    plt.title(
        "Random Forest: "
        "Top Feature Importances"
    )
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        / "feature_importance.png",
        dpi=150,
    )
    plt.close()

    return {
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "logistic_regression": log_metrics,
        "random_forest": rf_metrics,
        "top_features": [
            {
                "feature": row.feature,
                "importance": round(
                    float(row.importance),
                    4,
                ),
            }
            for row in (
                top_features.itertuples()
            )
        ],
    }


def generate_report(results):
    """Generate the required Markdown midterm report."""
    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    log = results["models"][
        "logistic_regression"
    ]
    rf = results["models"][
        "random_forest"
    ]

    best = (
        "Random Forest"
        if rf["f1"] >= log["f1"]
        else "Logistic Regression"
    )

    bad = int(
        results["class_counts"].get(
            "1",
            0,
        )
    )

    good = int(
        results["class_counts"].get(
            "0",
            0,
        )
    )

    total = bad + good

    bad_pct = (
        bad / total * 100
        if total
        else 0
    )

    top_text = ", ".join(
        item["feature"]
        .replace("numeric__", "")
        .replace("categorical__", "")
        for item in (
            results["models"][
                "top_features"
            ][:5]
        )
    )

    report = f"""# Midterm Report: Personal Finance Dashboard + Credit-Risk Data Science Analysis

## 1. Introduction to the Dataset

Our group expanded the existing Personal Finance & Budget Dashboard with a reproducible data-science analysis using the **South German Credit** dataset from the UCI Machine Learning Repository. The dataset contains financial and credit characteristics such as duration, amount, savings status, age, housing, employment duration, and credit history.

In the original UCI file, `credit_risk` is coded as 0 = bad and 1 = good. During preprocessing, this project reverses the coding to 0 = good and 1 = bad so that precision, recall, and F1 score describe the model's ability to identify bad-risk cases.

- Source: UCI Machine Learning Repository
- Dataset: South German Credit
- UCI dataset ID: {UCI_DATASET_ID}
- DOI: {UCI_DOI}
- Rows after cleaning: {results['cleaning']['final_rows']}
- Research question: Can financial and credit characteristics help classify good vs. bad credit risk?

## 2. Data Cleaning & Preprocessing Steps

- Duplicate records removed: {results['cleaning']['duplicate_rows_removed']}
- Missing cells before cleaning: {results['cleaning']['missing_cells_before_cleaning']}
- Invalid rows removed: {results['cleaning']['invalid_rows_removed']}
- Missing cells after cleaning: {results['cleaning']['missing_cells_after_cleaning']}

The project uses three preprocessing techniques: feature engineering (`amount_per_month` and `age_group`), standard scaling for numeric variables, and one-hot encoding for categorical variables.

## 3. EDA & Key Insights

The script runs `info()`, `describe()`, mean, median, standard deviation, correlations, and class-balance analysis. After cleaning, the data contain {good} good-risk records and {bad} bad-risk records. Bad-risk records represent approximately {bad_pct:.1f}% of the cleaned data.

The project generates five visualizations: a histogram, boxplot, correlation heatmap, class-balance bar chart, and Random Forest feature-importance bar chart.

## 4. Model Building & Evaluation

Both models use the same stratified 75/25 train-test split.

### Logistic Regression

- Accuracy: {log['accuracy']:.3f}
- Precision: {log['precision']:.3f}
- Recall: {log['recall']:.3f}
- F1 score: {log['f1']:.3f}

### Random Forest

- Accuracy: {rf['accuracy']:.3f}
- Precision: {rf['precision']:.3f}
- Recall: {rf['recall']:.3f}
- F1 score: {rf['f1']:.3f}

The project reports four evaluation metrics, exceeding the requirement of two. Accuracy measures overall correctness. Precision measures how often predicted bad-risk records are actually bad risk. Recall measures how many actual bad-risk records the model detects. F1 balances precision and recall.

Based on F1 score in this run, **{best}** performed better overall. The strongest Random Forest features included: {top_text}.

## 5. Conclusion

The final project combines the original Flask budget application with a full data-science pipeline. The dashboard demonstrates application development, while the analysis demonstrates acquisition, cleaning, preprocessing, EDA, visualization, two machine-learning algorithms, and evaluation.

The credit-risk models are an educational class exercise and should not be used to make real lending decisions.

## 6. References

- South German Credit [Dataset]. UCI Machine Learning Repository. {UCI_DOI}
- UCI dataset page: {UCI_DATASET_PAGE}
- Grömping, U. (2019). *South German Credit Data: Correcting a Widely Used Data Set.*
- pandas, NumPy, matplotlib, seaborn, and scikit-learn documentation.
"""

    path = (
        REPORT_DIR
        / "MIDTERM_REPORT.md"
    )

    path.write_text(
        report,
        encoding="utf-8",
    )

    return path


def main():
    """Run the complete data-science workflow."""
    for directory in [
        DATA_DIR,
        OUTPUT_DIR,
        MODEL_DIR,
        REPORT_DIR,
    ]:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    df = acquire_dataset()

    df, cleaning = clean_dataset(df)

    df = engineer_features(df)

    df.to_csv(
        CLEAN_DATA_FILE,
        index=False,
    )

    (
        stats,
        correlations,
        class_counts,
    ) = create_eda(df)

    models = train_models(df)

    results = {
        "dataset": {
            "name": "South German Credit",
            "source": (
                "UCI Machine Learning "
                "Repository"
            ),
            "uci_id": UCI_DATASET_ID,
            "page": UCI_DATASET_PAGE,
            "doi": UCI_DOI,
            "rows": len(df),
            "columns": len(df.columns),
        },
        "cleaning": cleaning,
        "preprocessing": [
            (
                "Feature engineering "
                "(amount_per_month and "
                "age_group)"
            ),
            (
                "Standard scaling for "
                "numeric variables"
            ),
            (
                "One-hot encoding for "
                "categorical variables"
            ),
        ],
        "class_counts": {
            str(key): int(value)
            for key, value
            in class_counts.items()
        },
        "descriptive_statistics": stats,
        "correlations": correlations,
        "models": models,
        "visualizations": [
            "amount_histogram.png",
            "duration_boxplot.png",
            "correlation_heatmap.png",
            "class_balance.png",
            "feature_importance.png",
        ],
    }

    RESULTS_FILE.write_text(
        json.dumps(
            results,
            indent=2,
        ),
        encoding="utf-8",
    )

    report_path = generate_report(
        results
    )

    print("\nAnalysis complete.")
    print(
        f"Results: {RESULTS_FILE}"
    )
    print(
        f"Report: {report_path}"
    )


if __name__ == "__main__":
    main()
