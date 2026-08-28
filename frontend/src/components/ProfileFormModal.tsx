import { useId, useState, type FormEvent } from "react";

import { getErrorMessage } from "../api/client";
import type { Profile, ProfileInput } from "../types";
import { Modal } from "./Modal";

interface ProfileFormModalProps {
  profile: Profile;
  initialSetup: boolean;
  onClose: () => void;
  onSubmit: (input: ProfileInput) => Promise<void>;
}

export function ProfileFormModal({
  profile,
  initialSetup,
  onClose,
  onSubmit,
}: ProfileFormModalProps) {
  const nameId = useId();
  const dailyGoalId = useId();
  const [displayName, setDisplayName] = useState(
    profile.is_configured ? profile.display_name : "",
  );
  const [dailyGoal, setDailyGoal] = useState(profile.daily_goal);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!displayName.trim()) {
      setError("사용할 이름을 입력해 주세요.");
      return;
    }
    if (!Number.isInteger(dailyGoal) || dailyGoal < 1 || dailyGoal > 100) {
      setError("하루 목표는 1개에서 100개 사이로 설정해 주세요.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        display_name: displayName.trim(),
        daily_goal: dailyGoal,
        timezone: profile.is_configured
          ? profile.timezone
          : Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Seoul",
      });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
      setSaving(false);
    }
  };

  return (
    <Modal
      title={initialSetup ? "내 프로필 만들기" : "프로필 설정"}
      description={
        initialSetup
          ? "로그인 없이 이 프로필 하나에 카드와 학습 기록을 저장합니다."
          : "대시보드에 표시할 이름과 하루 학습 목표를 관리합니다."
      }
      onClose={onClose}
      closeDisabled={saving || initialSetup}
      hideClose={initialSetup}
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field" htmlFor={nameId}>
          <span>이름</span>
          <input
            id={nameId}
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="예: 준혁"
            maxLength={80}
            autoFocus
            required
          />
        </label>

        <label className="field" htmlFor={dailyGoalId}>
          <span>하루 문제 목표</span>
          <input
            id={dailyGoalId}
            type="number"
            min={1}
            max={100}
            value={dailyGoal}
            onChange={(event) => setDailyGoal(Number(event.target.value))}
            required
          />
          <small>대시보드에서 오늘 푼 문제 수와 함께 보여드려요.</small>
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}

        <div className="modal-actions">
          {!initialSetup && (
            <button className="button button--ghost" type="button" onClick={onClose} disabled={saving}>
              취소
            </button>
          )}
          <button className="button button--primary" type="submit" disabled={saving}>
            {saving ? "저장 중…" : initialSetup ? "프로필 시작하기" : "설정 저장"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
