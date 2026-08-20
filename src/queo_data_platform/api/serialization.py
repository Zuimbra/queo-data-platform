from typing import cast

import pandas as pd


def dataframe_to_records(
    dataframe: pd.DataFrame,
) -> list[dict[str, object]]:
    """
    Converte um DataFrame para registros adequados
    à validação dos modelos HTTP.

    Valores ausentes do Pandas são convertidos
    explicitamente para None.
    """

    normalized = dataframe.astype(object).where(
        pd.notna(dataframe),
        None,
    )

    records = normalized.to_dict(orient="records")

    return cast(
        list[dict[str, object]],
        records,
    )
