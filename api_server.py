from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import pandas as pd
from config import Config
from data_fetcher import fetch_5min_kline
from calculator import calculate_vpu
from logger import logger

app = FastAPI(title="Stock-VPU API", version="1.0.0")


class StockRequest(BaseModel):
    code: str
    start_date: str
    end_date: str
    price_unit: float = 0.05
    trim_ratio: float = 0.25


@app.get("/")
async def root():
    return {"message": "Stock-VPU API is running"}


@app.post("/api/v1/calculate")
async def calculate_vpu_api(request: StockRequest):
    try:
        logger.info(f"API request for {request.code}")
        df = fetch_5min_kline(request.code, request.start_date, request.end_date)
        if df.empty:
            raise HTTPException(
                status_code=404, detail=f"No data found for {request.code}"
            )

        cfg = Config(PRICE_UNIT=request.price_unit, TRIM_RATIO=request.trim_ratio)
        result_df = calculate_vpu(df, cfg, code=request.code)

        result_df["date"] = result_df["date"].astype(str)
        return result_df.to_dict(orient="records")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
