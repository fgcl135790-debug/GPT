# exporters.py

import pandas as pd


class Exporter:

    @staticmethod
    def export_big_order_log(
        records,
        filename="big_order_log.csv"
    ):

        df = pd.DataFrame(records)

        return df.to_csv(
            index=False
        ).encode("utf-8-sig")
