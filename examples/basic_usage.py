import asyncio

import plotly.graph_objects as go
import polars as pl

from superset_client import SupersetClient
from superset_client.config import SupersetConfig


async def main():
    config = SupersetConfig()

    async with SupersetClient(config) as client:
        chart = await client.find_chart_by_name("Inappropriate UTI diagnosis (time series)")
        print(f"Found chart: {chart.slice_name} (ID: {chart.id})")

        response = await client.get_chart_data(chart.id)

        if not response.result:
            print("No data returned")
            return

        result = response.result[0]
        print(f"Columns: {result.colnames}")
        print(f"Row count: {result.rowcount}")

        if result.data:
            df = pl.DataFrame(result.data, schema=result.colnames)
            print(f"\nFirst few rows:\n{df.head()}")

            time_col = next(
                (col for col in result.colnames if "time" in col.lower() or "date" in col.lower()),
                None,
            )

            fig = go.Figure()

            if time_col:
                x_col = time_col
                y_cols = [col for col in result.colnames if col != time_col]

                if df[x_col].dtype == pl.Float64 or df[x_col].dtype == pl.Int64:
                    try:
                        df = df.with_columns(
                            pl.from_epoch(
                                (pl.col(time_col) / 1000).cast(pl.Int64), time_unit="s"
                            ).alias(time_col)
                        )
                        print("Converted timestamp from milliseconds to datetime")
                    except Exception as e:
                        print(f"Failed to convert timestamp: {e}")
                elif df[x_col].dtype == pl.String:
                    try:
                        df = df.with_columns(
                            pl.col(time_col).str.to_datetime("%Y-%m-%d %H:%M:%S%.f")
                        )
                        print("Successfully parsed with format: %Y-%m-%d %H:%M:%S%.f")
                    except Exception:
                        try:
                            df = df.with_columns(pl.col(time_col).str.to_datetime("%Y-%m-%d"))
                            print("Successfully parsed with format: %Y-%m-%d")
                        except Exception:
                            try:
                                df = df.with_columns(pl.col(time_col).str.to_datetime())
                                print("Successfully parsed with auto-detection")
                            except Exception:
                                pass
            else:
                x_col = result.colnames[0]
                y_cols = result.colnames[1:] if len(result.colnames) > 1 else result.colnames

            line_styles = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
            marker_symbols = ["circle", "square", "diamond", "triangle-up", "x", "cross"]

            for idx, col in enumerate(y_cols):
                fig.add_trace(
                    go.Scatter(
                        x=df[x_col],
                        y=df[col],
                        mode="lines+markers",
                        name=col,
                        line=dict(
                            color="black",
                            dash=line_styles[idx % len(line_styles)],
                            width=2,
                        ),
                        marker=dict(
                            symbol=marker_symbols[idx % len(marker_symbols)],
                            size=8,
                            color="black",
                        ),
                    )
                )

            fig.update_layout(
                title=chart.slice_name,
                xaxis_title=x_col,
                yaxis_title="Value",
                hovermode="x unified",
                plot_bgcolor="white",
                paper_bgcolor="white",
                xaxis=dict(
                    tickfont=dict(color="gray"),
                    gridcolor="lightgray",
                    linecolor="gray",
                    zerolinecolor="lightgray",
                ),
                yaxis=dict(
                    tickfont=dict(color="gray"),
                    gridcolor="lightgray",
                    linecolor="gray",
                    zerolinecolor="lightgray",
                ),
            )

            if time_col and df[x_col].dtype in (pl.Datetime, pl.Date):
                fig.update_xaxes(
                    tickformat="%b %Y",
                    dtick="M1",
                )

            fig.show()


if __name__ == "__main__":
    asyncio.run(main())
