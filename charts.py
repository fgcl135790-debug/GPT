import pandas as pd
import plotly.graph_objects as go

from plotly.subplots import make_subplots


class ChartBuilder:

    # =========================
    # EMA
    # =========================

    @staticmethod
    def calculate_ema(
        prices,
        span,
    ):

        if len(prices) == 0:

            return []

        return (

            pd.Series(prices)

            .ewm(

                span=span,

                adjust=False,

            )

            .mean()

            .tolist()

        )

    # =========================
    # SMA
    # =========================

    @staticmethod
    def calculate_sma(
        prices,
        period,
    ):

        if len(prices) == 0:

            return []

        return (

            pd.Series(prices)

            .rolling(period)

            .mean()

            .tolist()

        )

    # =========================
    # Price Chart
    # =========================

    @staticmethod
    def build_price_chart(

        prices,

        volumes,

    ):
        # =========================
        # EMA
        # =========================

        ema5 = ChartBuilder.calculate_ema(
            prices,
            5,
        )

        ema20 = ChartBuilder.calculate_ema(
            prices,
            20,
        )

        ema60 = ChartBuilder.calculate_ema(
            prices,
            60,
        )

        sma20 = ChartBuilder.calculate_sma(
            prices,
            20,
        )

        # =========================
        # Figure
        # =========================

        fig = make_subplots(

            rows=2,

            cols=1,

            shared_xaxes=True,

            vertical_spacing=0.03,

            row_heights=[0.75, 0.25],

        )

        # =========================
        # Price
        # =========================

        fig.add_trace(

            go.Scatter(

                y=prices,

                mode="lines",

                name="Price",

                line=dict(

                    color="#00E5FF",

                    width=3,

                ),

            ),

            row=1,

            col=1,

        )

        fig.add_trace(

            go.Scatter(

                y=ema5,

                mode="lines",

                name="EMA5",

                line=dict(

                    color="#FFD54F",

                    width=2,

                ),

            ),

            row=1,

            col=1,

        )

        fig.add_trace(

            go.Scatter(

                y=ema20,

                mode="lines",

                name="EMA20",

                line=dict(

                    color="#FF7043",

                    width=2,

                ),

            ),

            row=1,

            col=1,

        )

        fig.add_trace(

            go.Scatter(

                y=ema60,

                mode="lines",

                name="EMA60",

                line=dict(

                    color="#AB47BC",

                    width=2,

                ),

            ),

            row=1,

            col=1,

        )

        fig.add_trace(

            go.Scatter(

                y=sma20,

                mode="lines",

                name="SMA20",

                line=dict(

                    color="#4CAF50",

                    width=2,

                    dash="dot",

                ),

            ),

            row=1,

            col=1,

        )

        # =========================
        # 成交量
        # =========================

        volume_colors = []

        for i in range(len(volumes)):

            if i == 0:

                volume_colors.append("#26A69A")

            else:

                if prices[i] >= prices[i - 1]:

                    volume_colors.append("#26A69A")

                else:

                    volume_colors.append("#EF5350")

        fig.add_trace(

            go.Bar(

                y=volumes,

                name="Volume",

                marker_color=volume_colors,

                opacity=0.8,

            ),

            row=2,

            col=1,

        )

        # =========================
        # Layout
        # =========================

        fig.update_layout(

            template="plotly_dark",

            height=700,

            margin=dict(

                l=10,

                r=10,

                t=20,

                b=10,

            ),

            hovermode="x unified",

            legend=dict(

                orientation="h",

                y=1.05,

                x=0,

            ),

            xaxis=dict(

                showgrid=False,

            ),

            yaxis=dict(

                showgrid=True,

                gridcolor="rgba(255,255,255,0.08)",

            ),

            plot_bgcolor="#111111",

            paper_bgcolor="#111111",

        )

        fig.update_xaxes(

            showgrid=False,

            zeroline=False,

        )

        fig.update_yaxes(

            zeroline=False,

        )

        # =========================
        # 自動判斷趨勢背景
        # =========================

        if len(ema20) > 0 and len(ema60) > 0:

            if ema20[-1] > ema60[-1]:

                bg_color = "rgba(0,120,0,0.08)"

            else:

                bg_color = "rgba(180,0,0,0.08)"

            fig.add_vrect(

                x0=0,

                x1=max(len(prices) - 1, 1),

                fillcolor=bg_color,

                opacity=0.25,

                line_width=0,

                layer="below",

            )

        # =========================
        # 最高價
        # =========================

        if len(prices) > 0:

            high_price = max(prices)

            high_index = prices.index(high_price)

            fig.add_annotation(

                x=high_index,

                y=high_price,

                text=f"⬆ {high_price:.2f}",

                showarrow=True,

                arrowhead=2,

                font=dict(

                    size=12,

                    color="#00FF99",

                ),

                arrowcolor="#00FF99",

            )

        # =========================
        # 最低價
        # =========================

        if len(prices) > 0:

            low_price = min(prices)

            low_index = prices.index(low_price)

            fig.add_annotation(

                x=low_index,

                y=low_price,

                text=f"⬇ {low_price:.2f}",

                showarrow=True,

                arrowhead=2,

                font=dict(

                    size=12,

                    color="#FF5252",

                ),

                arrowcolor="#FF5252",

            )

        # =========================
        # 最新價格水平線
        # =========================

        if len(prices) > 0:

            fig.add_hline(

                y=prices[-1],

                line_dash="dash",

                line_color="#00E5FF",

                opacity=0.6,

            )

        # =========================
        # Layout 微調
        # =========================

        fig.update_yaxes(

            fixedrange=False,

            showspikes=True,

            spikemode="across",

            spikesnap="cursor",

        )

        fig.update_xaxes(

            showspikes=True,

            spikemode="across",

            spikesnap="cursor",

        )

        # =========================
        # Return
        # =========================

        return fig

