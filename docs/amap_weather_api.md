# 高德地图天气查询接口文档

## 接口基本信息

- **接口名称**：天气查询服务（Weather Info API）
- **API 地址**：`https://restapi.amap.com/v3/weather/weatherInfo`
- **请求方式**：`GET`
- **请求格式**：`application/x-www-form-urlencoded`
- **返回格式**：`JSON`

---

## 请求参数说明

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| key | String | 是 | 高德地图开放平台申请的 Web 服务 API Key |
| city | String | 是 | 城市编码（可使用城市中文名称、行政区划编码或 adcode） |
| extensions | String | 否 | 查询天气类型：`base` 表示实况天气，`all` 表示预报天气 |
| output | String | 否 | 返回数据格式：可选值 `JSON`（默认）或 `XML` |

---

## 示例请求

**实况天气：**
```
https://restapi.amap.com/v3/weather/weatherInfo?key=您的key&city=110101&extensions=base
```

**预报天气：**
```
https://restapi.amap.com/v3/weather/weatherInfo?key=您的key&city=110101&extensions=all
```

---

## 返回结果

### 一、实况天气（extensions=base）

```json
{
  "status": "1",
  "count": "1",
  "info": "OK",
  "infocode": "10000",
  "lives": [
    {
      "province": "北京市",
      "city": "朝阳区",
      "adcode": "110105",
      "weather": "晴",
      "temperature": "25",
      "winddirection": "西北",
      "windpower": "3",
      "humidity": "40",
      "reporttime": "2025-10-16 10:00:00"
    }
  ]
}
```

### 二、预报天气（extensions=all）

```json
{
  "status": "1",
  "count": "1",
  "info": "OK",
  "infocode": "10000",
  "forecasts": [
    {
      "city": "北京市",
      "adcode": "110000",
      "province": "北京市",
      "reporttime": "2025-10-16 10:00:00",
      "casts": [
        {
          "date": "2025-10-16",
          "week": "4",
          "dayweather": "多云",
          "nightweather": "晴",
          "daytemp": "26",
          "nighttemp": "15",
          "daywind": "西北",
          "nightwind": "西南",
          "daypower": "3",
          "nightpower": "2"
        }
      ]
    }
  ]
}
```

---

## 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| status | String | 返回状态：`1` 表示成功，`0` 表示失败 |
| info | String | 返回的状态信息，如“OK” |
| infocode | String | 状态码（10000 表示请求成功） |
| lives | Array | 实况天气信息（仅当 `extensions=base` 时返回） |
| forecasts | Array | 天气预报信息（仅当 `extensions=all` 时返回） |
| city / province | String | 城市/省份名称 |
| adcode | String | 城市编码 |
| weather / temperature / humidity | String | 天气状况 / 温度 / 湿度 |
| reporttime | String | 数据发布时间 |
| casts | Array | 各日预报信息（仅当 `extensions=all` 时存在） |

---

## 状态码参考

| 状态码 | 说明 |
|--------|------|
| 10000 | 请求成功 |
| 10001 | key 参数错误 |
| 10003 | 权限不足 |
| 10004 | 请求次数超限 |
| 10005 | IP不正确 |
| 10007 | 请求服务不存在 |
| 10008 | 参数无效 |
| 10009 | 签名错误 |
| 10010 | 请求过期 |
| 10011 | 无权限 |
| 10012 | key被删除 |

---

## 注意事项

- 每个 API Key 每日请求次数有限制（具体取决于高德账号配额）。
- 建议缓存结果，避免频繁请求。
- 查询天气时，请使用准确的行政区划编码（可通过行政区划查询 API 获取）。

---

## 参考链接

- [高德地图开放平台：天气查询服务](https://lbs.amap.com/api/webservice/guide/api/weatherinfo/)
