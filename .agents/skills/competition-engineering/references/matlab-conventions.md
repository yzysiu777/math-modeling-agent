# MATLAB 实现约定

与 Python 侧遵守**同一套输入输出契约**。写作手不应该看得出某个结果是哪种语言跑的。

## 目录

```text
q<k>/code/matlab/
├── run_EXP_OPT_003.m      每个实验一个入口脚本
├── lib/                   共用函数，每个文件一个函数
└── plot_FIG_001.m         绘图脚本，与计算分开
```

MATLAB 文件名不能带连字符，实验 ID 里的 `-` 换成 `_`：`EXP-OPT-003` →
`run_EXP_OPT_003.m`。文件里用注释写明对应的 `EXP-ID` 和 `spec_id`。

## 入口脚本骨架

```matlab
% run_EXP_OPT_003.m
% EXP-ID:  EXP-OPT-003
% spec_id: SPEC-A1-M03
% 说明：SPEC-A1-M03 的 intlinprog 实现

function run_EXP_OPT_003()
    SEED = 42;
    rng(SEED, 'twister');

    here = fileparts(mfilename('fullpath'));
    caseDir = fullfile(here, '..', '..', '..');        % cases/<case_id>/
    outDir  = fullfile(caseDir, 'experiments', 'outputs');

    data = loadInput(fullfile(caseDir, 'input', '...'));
    [solution, meta] = solve(data);
    writeOutputs(outDir, solution, meta);
    % 复算在 Python 侧进行，见 recompute-recipes.md
end
```

## 随机种子

```matlab
rng(42, 'twister');
```

放在入口最前面，种子值写进 metrics JSON 和 `board.md`。用到 `rand`、`randn`、
`randperm`、遗传算法、粒子群等一律适用。

## 结果落盘

**必须显式指定 UTF-8**，否则中文列名和内容会乱码：

```matlab
function writeOutputs(outDir, solution, meta)
    dataDir = fullfile(outDir, 'data');
    if ~exist(dataDir, 'dir'); mkdir(dataDir); end

    % CSV：列名与规格第 5 段逐字一致
    T = table(solution.facility_id, solution.demand_id, ...
              solution.assigned, solution.cost_yuan, ...
        'VariableNames', {'facility_id','demand_id','assigned','cost_yuan'});
    writetable(T, fullfile(dataDir, 'EXP-OPT-003_solution.csv'), ...
               'Encoding', 'UTF-8', 'WriteRowNames', false);

    % JSON 指标
    s = struct('exp_id','EXP-OPT-003', 'spec_id','SPEC-A1-M03', ...
               'language','matlab', 'objective', meta.obj, ...
               'feasible', meta.feasible, 'runtime_sec', meta.t, 'seed', 42);
    fid = fopen(fullfile(dataDir, 'EXP-OPT-003_metrics.json'), 'w', 'n', 'UTF-8');
    fwrite(fid, jsonencode(s, 'PrettyPrint', true));
    fclose(fid);
end
```

要点：

- `writetable` 必须带 `'Encoding','UTF-8'`；
- 不写行名（`WriteRowNames` 为 false），Python 侧不期待行索引列；
- 缺失值用空字段：`writetable` 默认把 `NaN` 写成空，符合约定；
- `jsonencode` 的逻辑值会写成 `true`/`false`，与 Python 侧一致。

## 求解器要点

| 函数 | 适用 | 注意 |
|---|---|---|
| `intlinprog` | 混合整数线性规划 | `exitflag` 必须检查；`1` 才是收敛到最优 |
| `linprog` | 线性规划 | 同上；默认 `dual-simplex` |
| `fmincon` | 非线性约束优化 | 局部解，多起点验证；`exitflag <= 0` 不是解 |
| `ga` / `particleswarm` | 全局启发式 | 必须设 `rng` 和 `MaxTime`；结果不稳定要多次取统计 |
| `ode45` / `ode15s` | 常微分方程 | 刚性问题用 `ode15s`；记录 `RelTol`/`AbsTol` |
| `lsqcurvefit` | 曲线拟合 | 记录初值，初值敏感 |

**`exitflag` 必须检查并记录**：

```matlab
[x, fval, exitflag, output] = intlinprog(f, intcon, A, b, Aeq, beq, lb, ub, opts);
meta.feasible = (exitflag == 1);
meta.exitflag = exitflag;
meta.message  = output.message;
```

`exitflag` 不是 `1` 却把 `x` 当成解写进论文，是很难被发现的错误。

时间上限一律显式设：

```matlab
opts = optimoptions('intlinprog', 'MaxTime', 300, 'Display', 'iter');
```

## 复算

**MATLAB 侧不做最终复算。** 导出 CSV/JSON 后由 Python 复算并写
`outputs/checks/<EXP-ID>.json` —— 阶段检查和 CI 只能运行 Python。

用另一种语言独立重算，本身也是比同语言重算更强的验证。

MATLAB 侧可以做即时自检（约束残差、目标值重算）辅助调试，但这些不能代替
Python 侧的复算报告。

## 不做的事

- 不用 `clear all` / `close all` 开头的脚本式写法 —— 用函数，避免工作区污染；
- 不依赖当前工作目录，用 `mfilename('fullpath')` 定位；
- 不用 Live Script（`.mlx`）做主实现，二进制格式无法做 diff 和版本对比；
- 不在 MATLAB 里调 Python 引擎或反之，用文件交换。
