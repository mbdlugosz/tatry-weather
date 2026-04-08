from __future__ import annotations

import json
import os
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_AI_RISK_MODEL = "gpt-4o-mini"


class RiskAssessmentResult(BaseModel):
    matched_point_id: str = Field(description="Id najlepiej dopasowanego punktu, np. P001")
    matched_point_label: str = Field(description="Pelna etykieta dopasowanego punktu")
    match_reason: str = Field(description="Krotkie wyjasnienie po polsku, dlaczego ten punkt zostal wybrany")
    recommendation: Literal["safe", "risky", "dangerous"] = Field(
        description="Ocena ryzyka dla wskazanego punktu"
    )
    justification: list[str] = Field(description="2-4 krotkie powody decyzji po polsku")


def get_ai_risk_client() -> OpenAI:
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Brakuje zmiennej srodowiskowej OPENROUTER_API_KEY.")

    return OpenAI(
        base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
        api_key=api_key,
    )


def prepare_ai_point_payload(
    forecast_df: pd.DataFrame,
    point_catalog_df: pd.DataFrame,
    *,
    start_time: pd.Timestamp | str,
    horizon_steps: int = 8,
) -> list[dict]:
    if forecast_df.empty or point_catalog_df.empty:
        return []

    start_timestamp = pd.Timestamp(start_time)
    filtered_df = forecast_df[forecast_df["forecast_time"] >= start_timestamp].copy()
    if filtered_df.empty:
        return []

    metadata_columns = ["point_id", "point_label", "point_description", "point_display"]
    if set(metadata_columns).issubset(filtered_df.columns):
        merged_df = filtered_df.copy()
    else:
        merged_df = filtered_df.merge(
            point_catalog_df[
                ["point_id", "point_label", "point_description", "point_display", "lat", "lon"]
            ],
            on=["lat", "lon"],
            how="left",
        )

    payload: list[dict] = []
    for point in merged_df.sort_values(["point_id", "forecast_time"]).groupby("point_id", sort=True):
        point_id, point_df = point
        limited_df = point_df.head(horizon_steps).copy()
        if limited_df.empty:
            continue

        temperatures = {
            pd.Timestamp(row.forecast_time).strftime("%Y-%m-%d %H:%M:%S"): float(row.temperature)
            for row in limited_df.itertuples(index=False)
        }
        first_row = limited_df.iloc[0]
        payload.append(
            {
                "point_id": point_id,
                "point_label": first_row["point_label"],
                "point_display": first_row["point_display"],
                "point_description": first_row["point_description"],
                "lat": round(float(first_row["lat"]), 6),
                "lon": round(float(first_row["lon"]), 6),
                "forecast_window_start": pd.Timestamp(limited_df["forecast_time"].min()).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "forecast_window_end": pd.Timestamp(limited_df["forecast_time"].max()).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "temperature_min": round(float(limited_df["temperature"].min()), 2),
                "temperature_max": round(float(limited_df["temperature"].max()), 2),
                "temperatures": temperatures,
            }
        )

    return payload


def assess_tatra_risk(
    point_payload: list[dict],
    *,
    selected_point_id: str | None = None,
    point_description: str | None = None,
    model: str | None = None,
) -> RiskAssessmentResult:
    if not point_payload:
        raise ValueError("Brak danych prognozy do oceny ryzyka.")

    normalized_point_id = (selected_point_id or "").strip()
    normalized_description = (point_description or "").strip()
    if not normalized_point_id and not normalized_description:
        raise ValueError("Podaj opis lokalizacji.")

    system_message = (
        "Dokonujesz oceny ryzyka wedrowki gorskiej dla wskazanego punktu w Tatrach. "
        "Otrzymujesz komplet danych 24-godzinnej prognozy temperatur dla wszystkich punktow siatki. "
        "Jesli dostajesz point_id, oceniasz dokladnie ten punkt. "
        "Jesli dostajesz opis lokalizacji, dopasowujesz najbardziej prawdopodobny punkt na podstawie "
        "opisu, polozenia wzgledem obszaru i najblizszego punktu odniesienia. "
        "Zwroc wylacznie ustrukturyzowana odpowiedz. Wszystkie pola tekstowe wypelnij po polsku. "
        "Uzasadnienie ma byc krotkie, konkretne i zrozumiale dla uzytkownika dashboardu. "
        "W rekomendacji uzywaj tylko: safe, risky, dangerous."
    )

    user_payload = {
        "selected_point_id": normalized_point_id or None,
        "point_description": normalized_description or None,
        "points": point_payload,
    }

    client = get_ai_risk_client()
    response = client.responses.parse(
        model=model or os.getenv("AI_RISK_MODEL", DEFAULT_AI_RISK_MODEL),
        input=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
        ],
        text_format=RiskAssessmentResult,
    )
    return response.output_parsed
