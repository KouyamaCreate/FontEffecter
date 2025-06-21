"""
base_effect.py

全エフェクトプラグインが継承すべき抽象基底クラス。
"""

from abc import ABC, abstractmethod

class BaseEffect(ABC):
    def __init__(self, params=None):
        """
        エフェクトの基底クラス。パラメータを受け取って初期化する。
        """
        self.params = params if params is not None else {}
    
    @abstractmethod
    def apply(self, font, **kwargs):
        """
        フォントオブジェクトにエフェクトを適用し、変更後のフォントオブジェクトを返す。
        """
        pass