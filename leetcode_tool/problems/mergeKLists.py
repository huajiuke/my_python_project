"""合并 K 个升序链表
LeetCode 23. Merge k Sorted Lists
"""
from heapq import heapify, heappop, heappush
from typing import Optional, List

from leetcode_tool.structures import ListNode
from leetcode_tool import create_list_node, list_node_to_list
from leetcode_tool.runner import run_test


class Solution:
    def mergeKLists(self, lists: List[Optional[ListNode]]) -> Optional[ListNode]:
        """合并 K 个升序链表（堆解法）"""
        dummy = ListNode(-1)
        p = dummy
        heap = [(head.val, i, head) for i, head in enumerate(lists) if head]
        heapify(heap)

        while heap:
            val, i, node = heappop(heap)
            if node.next:
                heappush(heap, (node.next.val, i, node.next))
            p.next = node
            p = p.next

        return dummy.next


def to_listnode_list(lists: List[List[int]]) -> List[ListNode]:
    return [create_list_node(lst) for lst in lists]


# 实例化 Solution，把方法传进去
run_test(
    Solution().mergeKLists,
    [
        (([[1, 4, 5], [1, 3, 4], [2, 6]],), [1, 1, 2, 3, 4, 4, 5, 6]),
        (([],), []),
        (([[]],), []),
    ],
    input_transform=to_listnode_list,
    output_transform=list_node_to_list,
)
