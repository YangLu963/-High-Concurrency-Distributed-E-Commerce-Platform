-- KEYS[1]: 库存key
-- ARGV[1]: 预占数量
-- ARGV[2]: 预占ID
-- 返回值: 1-成功 0-库存不足 -1-其他错误

local inventoryKey = KEYS[1]
local reserveAmount = tonumber(ARGV[1])
local reserveId = ARGV[2]

-- 获取当前库存
local current = redis.call('HMGET', inventoryKey, 'available', 'reserved')
local available = tonumber(current[1])
local reserved = tonumber(current[2])

-- 检查库存是否足够
if available < reserveAmount then
    return 0
end

-- 执行预占
local newAvailable = available - reserveAmount
local newReserved = reserved + reserveAmount

-- 更新库存
redis.call('HMSET', inventoryKey,
    'available', newAvailable,
    'reserved', newReserved,
    'version', math.random(100000, 999999)
)

-- 记录预占日志
local reserveKey = 'inventory:reserve:' .. reserveId
redis.call('HSET', reserveKey,
    'sku', redis.call('HGET', inventoryKey, 'skuCode'),
    'amount', reserveAmount,
    'status', 'RESERVED',
    'expire', redis.call('TIME')[1] + 3600 -- 1小时过期
)

return 1