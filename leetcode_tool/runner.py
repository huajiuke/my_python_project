"""LeetCode 本地测试运行器"""

import time
import sys


def _format_value(val, max_len: int = 80) -> str:
    """将值格式化为可读字符串"""
    s = repr(val)
    if len(s) > max_len:
        s = s[:max_len] + "..."
    return s


def run_test(
    solution_func,
    testcases: list,
    *,
    input_transform=None,
    output_transform=None,
    equal=None,
):
    """运行测试用例并打印结果。

    参数:
        solution_func: 待测试的解题函数
        testcases: 测试用例列表，每项为 (input, expected)
            input 可以是:
              - 元组: (arg1, arg2, ...)  → 作为 *args 传入
              - 字典: {"key": val}        → 作为 **kwargs 传入
              - 其他: 单个值             → 作为唯一参数传入
        input_transform: 可选，对 input 中的每个参数做预转换
        output_transform: 可选，对返回值做转换后再与 expected 比较
        equal: 可选，自定义比较函数，默认用 ==
    """
    total = len(testcases)
    passed = 0
    failed = 0
    errors = 0

    print("=" * 56)
    print(f"  测试函数: {solution_func.__name__}")
    print(f"  测试用例: {total}")
    print("=" * 56)

    for i, (inputs, expected) in enumerate(testcases, 1):
        # 对输入做预转换
        args = ()
        kwargs = {}
        if isinstance(inputs, dict):
            kwargs = inputs
            if input_transform:
                kwargs = {k: input_transform(v) if not isinstance(v, (list, tuple)) or k != "self" else v for k, v in inputs.items()}
        elif isinstance(inputs, tuple):
            args = inputs
            if input_transform:
                args = tuple(input_transform(a) for a in inputs)
        else:
            args = (inputs,)
            if input_transform:
                args = (input_transform(inputs),)

        # 执行
        start = time.time()
        try:
            if kwargs:
                result = solution_func(**kwargs)
            else:
                result = solution_func(*args)

            # 对结果做转换（例如链表转数组后再比较）
            actual = result
            if output_transform:
                actual = output_transform(result)

            # 比较
            is_equal = (actual == expected) if equal is None else equal(actual, expected)

            cost_ms = (time.time() - start) * 1000

            if is_equal:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"

        except Exception as e:
            errors += 1
            status = "ERROR"
            actual = f"{type(e).__name__}: {e}"
            cost_ms = (time.time() - start) * 1000

        # 打印单条结果
        if status == "PASS":
            tag = "  PASS"
        elif status == "FAIL":
            tag = "  FAIL"
        else:
            tag = " ERROR"

        print(f" #{i:2d} {tag} | {cost_ms:6.1f}ms | {_format_value(expected, 50)}")

        if status == "FAIL":
            print(f"      期望: {_format_value(expected)}")
            print(f"      实际: {_format_value(actual)}")
        elif status == "ERROR":
            print(f"      错误: {actual}")

    # 汇总
    print("=" * 56)
    all_pass = passed == total
    if all_pass:
        print(f"  结果: 全部通过 ({passed}/{total})")
    else:
        print(f"  结果: {passed} 通过, {failed} 失败, {errors} 错误 / 共 {total}")
    print("=" * 56)

    return all_pass
