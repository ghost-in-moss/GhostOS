from ghostos.framework.operators.action_ops import (
    WaitsOperator,
    FailOperator,
    FinishOperator,
    ThinkOperator,
    WaitOnTasksOperator,
)
from ghostos.framework.operators.event_ops import (
    # 统一的事件状态机.
    OnEventOperator,

    # 上游相关事件. 
    OnUpstreamEventOperator,
    OnInputOperator,
    OnCancelingOperator,
    OnCreatedOperator,

    # 自身的事件. 
    OnSelfEventOperator,
    OnObserveOperator,

    # 下游的 callback 事件. 
    OnCallbackEventOperator,
    OnFinishCallbackOperator,
    OnNotifyCallbackOperator,
    OnWaitCallbackOperator,
    OnFailureCallbackOperator,
)
