
-- KEYS[1]: 库存key
-- KEYS[2]: 操作日志key
-- ARGV[1]: 回滚数量
-- ARGV[2]: 原始操作ID
-- 返回值: 1-成功 0-操作不存在 -1-其他错误

local inventoryKey = KEYS[1]
local opLogKey = KEYS[2]
local rollbackAmount = tonumber(ARGV[1])
local originalOpId = ARGV[2]

-- 检查原始操作是否存在
local originalOp = redis.call('HGETALL', 'inventory:op:' .. originalOpId)
if not originalOp or #originalOp == 0 then
    return 0
end

-- 获取当前库存
local current = redis.call('HMGET', inventoryKey, 'total', 'available')
local total = tonumber(current[1])
local available = tonumber(current[2])

-- 执行回滚
local newAvailable = available + rollbackAmount
local newTotal = total + rollbackAmount

-- 更新库存
redis.call('HMSET', inventoryKey,
    'total', newTotal,
    'available', newAvailable,
    'version', math.random(100000, 999999)
)

-- 记录回滚日志
redis.call('HSET', opLogKey,
    'opType', 'ROLLBACK',
    'amount', rollbackAmount,
    'originalOp', originalOpId,
    'before', available,
    'after', newAvailable,
    'time', redis.call('TIME')[1]
)

-- 标记原始操作为已回滚
redis.call('HSET', 'inventory:op:' .. originalOpId, 'status', 'ROLLBACKED')

return 1