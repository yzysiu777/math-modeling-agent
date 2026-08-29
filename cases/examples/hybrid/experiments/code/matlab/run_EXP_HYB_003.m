% run_EXP_HYB_003.m
% EXP-ID:  EXP-HYB-003
% spec_id: SPEC-P2-M01
% 说明：预测驱动的库存决策，MATLAB 主实现。
%
% 本文件演示跨语言契约：MATLAB 负责求解并按约定格式导出 CSV/JSON，
% Python 侧的 recompute_EXP_HYB_003.py 读入后独立复算并写复算报告。
% 阶段检查与 CI 只能运行 Python，因此 MATLAB 侧不写复算报告。
%
% 运行：在本目录下执行 run_EXP_HYB_003

function run_EXP_HYB_003()
    SEED = 42;
    rng(SEED, 'twister');

    EXP_ID  = 'EXP-HYB-003';
    SPEC_ID = 'SPEC-P2-M01';

    % 规格第 3 段的参数
    CAPACITY      = 10;   % 仓储容量，单位：units
    HOLDING_COST  = 1;    % 单位持有成本，单位：成本单位/unit
    SHORTAGE_COST = 5;    % 单位缺货惩罚，单位：成本单位/unit
    FORECAST      = 8;    % 上游点预测需求，单位：units
    STRESS        = [6 8 10];  % 需求扰动场景，单位：units

    here    = fileparts(mfilename('fullpath'));
    caseDir = fullfile(here, '..', '..', '..');
    dataDir = fullfile(caseDir, 'experiments', 'outputs', 'data');
    if ~exist(dataDir, 'dir'); mkdir(dataDir); end

    tic;
    [quantity, objective] = solveInventory(FORECAST, CAPACITY, HOLDING_COST, SHORTAGE_COST);
    runtime = toc;

    % 压力测试：备货量固定在点预测下的最优值，观察需求偏离时的成本
    stressCost = arrayfun(@(d) inventoryCost(quantity, d, HOLDING_COST, SHORTAGE_COST), STRESS);

    % --- CSV：列名与规格第 5 段逐字一致，UTF-8，不写行名 ---
    T = table(repmat(string(EXP_ID), numel(STRESS), 1), STRESS(:), ...
              repmat(quantity, numel(STRESS), 1), stressCost(:), ...
        'VariableNames', {'exp_id', 'demand_units', 'quantity_units', 'cost_yuan'});
    writetable(T, fullfile(dataDir, [EXP_ID '_solution.csv']), ...
               'Encoding', 'UTF-8', 'WriteRowNames', false);

    % --- JSON 指标：字段与 Python 侧共享格式一致 ---
    metrics = struct( ...
        'exp_id',       EXP_ID, ...
        'spec_id',      SPEC_ID, ...
        'language',     'matlab', ...
        'objective',    objective, ...
        'feasible',     quantity >= 0 && quantity <= CAPACITY, ...
        'runtime_sec',  runtime, ...
        'seed',         SEED, ...
        'quantity',     quantity, ...
        'forecast',     FORECAST, ...
        'capacity',     CAPACITY, ...
        'holding_cost', HOLDING_COST, ...
        'shortage_cost', SHORTAGE_COST);
    fid = fopen(fullfile(dataDir, [EXP_ID '_metrics.json']), 'w', 'n', 'UTF-8');
    fwrite(fid, jsonencode(metrics, 'PrettyPrint', true));
    fclose(fid);

    fprintf('WROTE %s\n', fullfile(dataDir, [EXP_ID '_solution.csv']));
    fprintf('下一步：python ../python/recompute_EXP_HYB_003.py 做独立复算\n');
end


function c = inventoryCost(quantity, demand, holding, shortage)
    % 规格第 2 段的目标函数：持有成本 + 缺货惩罚
    c = quantity * holding + max(demand - quantity, 0) * shortage;
end


function [bestQuantity, bestCost] = solveInventory(demand, capacity, holding, shortage)
    % 规格第 4 段：容量范围内枚举，规模极小，无需求解器
    candidates = 0:capacity;
    costs = arrayfun(@(q) inventoryCost(q, demand, holding, shortage), candidates);
    [bestCost, idx] = min(costs);
    bestQuantity = candidates(idx);
end
