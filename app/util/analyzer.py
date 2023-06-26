import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from io import BytesIO


def generate_plots(opinions):
    opinions = pd.DataFrame(opinions)

    plt.figure(figsize=(10, 6))

    stars = opinions.stars.value_counts().reindex(
        list(np.arange(0.5, 5.5, 0.5)), fill_value=0
    )

    stars.plot.bar(color="royalblue")
    for index, value in enumerate(stars):
        plt.text(index, value + 1, str(value), ha="center")
    plt.ylim(0, max(stars.values) * 1.1)
    plt.xticks(rotation=0)
    plt.grid(axis="y", which="major")
    plt.xlabel("Number of stars")
    plt.ylabel("Number of opinions")
    plt.title("Stars Frequency")

    stars_image = BytesIO()
    plt.savefig(stars_image, format="png")
    plt.close()

    recommendations = opinions.recommendation.value_counts(dropna=False).reindex(
        [True, False, np.nan]
    )
    recommendations.plot.pie(
        label="",
        labels=["Recommended", "Not Recommended", "Neutral"],
        colors=["green", "crimson", "lightgrey"],
        autopct=lambda p: "{:.1f}%".format(round(p)) if p > 0 else "",
    )
    plt.title("Recommendations")

    recommendations_image = BytesIO()
    plt.savefig(recommendations_image, format="png")
    plt.close()

    plots = {
        "stars": stars_image.getvalue(),
        "recommendations": recommendations_image.getvalue(),
    }

    return plots
