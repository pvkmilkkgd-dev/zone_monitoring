import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../apiClient";

export function RegisterPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!username || !password || !passwordConfirm) {
      setError("�-�����?�>�?��'�� �?�?�� ���?�>�?");
      return;
    }

    if (password !== passwordConfirm) {
      setError("�?���?�?�>�� �?�� �?�?�?�����?���?�'");
      return;
    }

    setIsSubmitting(true);

    try {
      const data = await apiRequest<{ username: string }>(
        "/auth/register",
        "POST",
        {
          username,
          password,
        }
      );
      setSuccess(`�?�?�>�?���?�?���'��>�? ${data.username} �?�?����?�?�? �����?��?��?�'�?��?�?�?���?`);
      setUsername("");
      setPassword("");
      setPasswordConfirm("");
    } catch (e: any) {
      setError(
        e.message ||
          "��'�?-�'�? ���?�?�>�? �?�� �'���� ���?�� �?��?��?�'�?���Ő��"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <h1 className="auth-title">Zone Monitoring</h1>
      <p className="auth-subtitle">����?��?�'�?���Ő�? ���?�>�?���?�?���'��>�?</p>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label className="auth-label">
          �?�?�? ���?�>�?���?�?���'��>�?
          <input
            type="text"
            className="auth-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="�'�?��?��'�� ��?�?"
          />
        </label>

        <label className="auth-label">
          �?���?�?�>�?
          <input
            type="password"
            className="auth-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="�'�?��?��'�� �����?�?�>�?"
          />
        </label>

        <label className="auth-label">
          �?�?�?�'�?�?��'�� �����?�?�>�?
          <input
            type="password"
            className="auth-input"
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            placeholder="�?�?�?�'�?�?��'�� �����?�?�>�?"
          />
        </label>

        {error && <div className="auth-message auth-error">{error}</div>}
        {success && <div className="auth-message auth-success">{success}</div>}

        <button className="auth-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "�?�'���?���?���..." : "�-���?��?��?�'�?��?�?�?���'�?�?�?"}
        </button>

        <p style={{ marginTop: 16 }}>
          �?��� ��?�'�? �?�ؑ'�'�?���? ��������?�??{" "}
          <Link to="/login">�'�?���'��</Link>
        </p>
      </form>
    </>
  );
}

export default RegisterPage;
