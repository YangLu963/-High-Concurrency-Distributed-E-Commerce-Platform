-- KEYS[1]: 库存key
-- ARGV[1]: 扣减数量
-- ARGV[2]: 订单ID
-- 返回值: 1-成功 0-库存不足 -1-其他错误

local inventoryKey = KEYS[1]
local deductAmount = tonumber(ARGV[1])
local orderId = ARGV[2]

-- 获取当前库存
local current = redis.call('HMGET', inventoryKey, 'total', 'available', 'reserved')
local total = tonumber(current[1])
local available = tonumber(current[2])
local reserved = tonumber(current[3])

-- 检查库存是否足够
if available < deductAmount then
    return 0
end

-- 执行扣减
local newAvailable = available - deductAmount
local newTotal = total - deductAmount

-- 更新库存
redis.call('HMSET', inventoryKey,
    'total', newTotal,
    'available', newAvailable,
    'version', math.random(100000, 999999) -- 模拟版本号变更
)

-- 记录操作日志
local logKey = 'inventory:op:' .. orderId
redis.call('HSET', logKey,
    'sku', redis.call('HGET', inventoryKey, 'skuCode'),
    'opType', 'DEDUCT',
    'amount', deductAmount,
    'before', available,
    'after', newAvailable,
    'time', redis.call('TIME')[1]
)

return 1