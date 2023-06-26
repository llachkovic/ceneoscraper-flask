import os
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_plots(opinions, product_code):
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

    # Save stars plot as a file
    stars_filename = f"app/static/images/{product_code}_stars.png"
    os.makedirs(os.path.dirname(stars_filename), exist_ok=True)
    plt.savefig(stars_filename)
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

    # Save recommendations plot as a file
    recommendations_filename = f"app/static/images/{product_code}_rcmds.png"
    plt.savefig(recommendations_filename)
    plt.close()

    return stars_filename, recommendations_filename
