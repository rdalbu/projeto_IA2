import collections
import math
from . import constants

class GestureRecognizer:
    def __init__(self, swipe_threshold=70, pinch_threshold=30, max_history_length=10):
        self.swipe_threshold = swipe_threshold
        self.pinch_threshold = pinch_threshold
        self.hand_history = collections.deque(maxlen=max_history_length)

    def update_history(self, hand_landmarks):
        if hand_landmarks and len(hand_landmarks) > constants.MIDDLE_FINGER_TIP:
            # Usar o ponto médio entre o dedo indicador e o médio para o deslize
            ponto_indicador_x = hand_landmarks[constants.INDEX_FINGER_TIP][1]
            ponto_medio_x = hand_landmarks[constants.MIDDLE_FINGER_TIP][1]
            ponto_medio_dedos_x = (ponto_indicador_x + ponto_medio_x) // 2
            self.hand_history.append(ponto_medio_dedos_x)
        else:
            self.hand_history.clear()

    def recognize_gesture(self, hand_landmarks):
        if not hand_landmarks or len(hand_landmarks) < 21:
            return None

        # Priorizar o gesto de pinça, pois é muito específico
        if self._is_pinch(hand_landmarks):
            return "Pinca"

        raised_fingers = self._get_raised_fingers(hand_landmarks)
        total_fingers = sum(raised_fingers)

        # Gestos dinâmicos apenas com 2 dedos levantados
        if total_fingers == 2:
            dynamic_gesture = self._recognize_dynamic_gesture()
            if dynamic_gesture:
                return dynamic_gesture

        if total_fingers == 5:
            return "Mao Aberta"

        return None

    def _get_raised_fingers(self, hand_landmarks):
        fingers = []

        # Polegar (lógica diferente, verifica pela posição x)
        if hand_landmarks[constants.THUMB_TIP][1] > hand_landmarks[constants.THUMB_IP][1]:
            fingers.append(1)
        else:
            fingers.append(0)

        # Outros 4 dedos (verifica pela posição y)
        for i in range(1, 5):
            tip_y = hand_landmarks[constants.TIPS[i]][2]
            pip_y = hand_landmarks[constants.PIPS[i]][2]
            if tip_y < pip_y:
                fingers.append(1)
            else:
                fingers.append(0)
        return fingers

        def _is_pinch(self, hand_landmarks):
            thumb_tip = hand_landmarks[constants.THUMB_TIP]
            index_tip = hand_landmarks[constants.INDEX_FINGER_TIP]
    
            distance = math.hypot(thumb_tip[1] - index_tip[1], thumb_tip[2] - index_tip[2])
    
            return distance < self.pinch_threshold
    def _recognize_dynamic_gesture(self):
        if len(self.hand_history) < self.hand_history.maxlen:
            return None

        difference = self.hand_history[-1] - self.hand_history[0]

        if difference > self.swipe_threshold:
            self.hand_history.clear()
            return "Deslizar Direita"
        elif difference < -self.swipe_threshold:
            self.hand_history.clear()
            return "Deslizar Esquerda"

        return None
