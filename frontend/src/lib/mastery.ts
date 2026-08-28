// 개념 숙련도 색: cividis 계열(파랑→노랑) 순차 램프. 색약 안전하고
// 타입 팔레트(초록/빨강/앰버)와 겹치지 않아 오개념 노드와 혼동되지 않는다.
// 그래프 노드와 대시보드 "약한 개념" 패널이 같은 색 언어를 쓰도록 여기서 공유한다.
export const MASTERY_RAMP = ["#00204d", "#414d6b", "#7c7b78", "#bcaf6f", "#ffe945"];
export const UNATTEMPTED_COLOR = "#f0f4f2";
// graded_count가 이 값 미만이면 "표본 적음"으로 흐리게 표시(백엔드 LOW_SAMPLE_THRESHOLD와 일치).
export const LOW_SAMPLE_THRESHOLD = 3;

export function masteryColor(score: number | null): string {
  if (score == null) return UNATTEMPTED_COLOR;
  const clamped = Math.min(1, Math.max(0, score));
  const index = Math.min(
    MASTERY_RAMP.length - 1,
    Math.floor(clamped * MASTERY_RAMP.length),
  );
  return MASTERY_RAMP[index];
}
