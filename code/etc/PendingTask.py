from __future__ import annotations

import asyncio
import dill
import os
import hashlib

from typing import BinaryIO, List, Callable, Any, Optional, Tuple


running_tasks = []



def load() -> List[PendingTask]:
    tasks = []
    if os.path.exists('pending/tasks.pnd'):
        with open('pending/tasks.pnd', 'rb') as file:
            while True:
                try:
                    func = dill.load(file)
                    args = dill.load(file)
                    tasks.append(PendingTask(func, *args))
                
                except EOFError:
                    break
    return tasks
    

def terminate(task: PendingTask) -> None:
    tasks = load()
    tasks.remove(task)
    
    with open('pending/tasks.pnd', 'wb') as file:
        for task in tasks:
            task._save(file)
        

async def run_task(task: PendingTask) -> None:
    running_tasks.append(task)
    task.start()
    if task.task:
        await task.task
    terminate(task)
    
    
async def run_new_task(func: Callable, *args: Any):
    if asyncio.iscoroutinefunction(func):
        await func(*args)
    else:
        func(*args)
            

async def run_tasks() -> None:
    for task in load():
        running_tasks.append(task)
        asyncio.create_task(run_task(task))
            

async def run_new_tasks() -> None:
    for task in load():
        if not task in running_tasks:
            asyncio.create_task(run_task(task))



class PendingTask:
    func: Callable
    args: Tuple[Any, ...]
    task: Optional[asyncio.Task]
    task_id: str
    

    def __init__(self, func, *args):
        self._filename = 'pending/tasks.pnd'
        self.func = func
        self.args = args
        self.task = None
        self.task_id = self._get_task_id()

    def _get_task_id(self):
        task_id = hashlib.md5(dill.dumps(self.func) + dill.dumps(self.args)).hexdigest()
        return task_id

    def start(self):
        if not self.task or self.task.done():
            self.task = asyncio.create_task(run_new_task(self.func, *self.args))

    def stop(self):
        if self.task and not self.task.done():
            self.task.cancel()

    def _save(self, file: BinaryIO):
        dill.dump(self.func, file)
        dill.dump(self.args, file)

    def save(self) -> None:
        with open(self._filename, 'ab') as file:
            self._save(file)
            
    def __eq__(self, other: PendingTask): # type: ignore
        return self.task_id == other.task_id