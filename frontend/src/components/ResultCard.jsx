import { ClinicIcon, HomeIcon, MapPinIcon, PhoneIcon } from './AppIcons.jsx';

export default function ResultCard({ result }) {
  const status = (result.status || 'in_progress').toLowerCase();
  const isVet = result.kind === 'vet';
  const label = isVet ? 'Vet clinic call' : 'Foster care call';
  const Icon = isVet ? ClinicIcon : HomeIcon;

  return (
    <article className={`card call-card ${isVet ? 'vet' : 'foster'}`}>
      <div className="icon-wrap" aria-hidden>
        <Icon size={20} />
      </div>
      <div className="body">
        <div className="row">
          <span className="title">{result.placeName || 'Calling…'}</span>
          <span className="spacer" />
          <span className={`status-badge ${status}`}>
            {status.replace('_', ' ')}
          </span>
        </div>
        <div className="card-meta">{label}</div>

        {result.summary && <p className="summary">{result.summary}</p>}

        <div className="meta">
          {result.available != null && (
            <span>{result.available ? '✓ Available' : '✗ Unavailable'}</span>
          )}
          {result.wait_minutes != null && (
            <span>~{result.wait_minutes} min</span>
          )}
          {result.placePhone && (
            <span className="meta-with-icon">
              <PhoneIcon size={13} />
              {result.placePhone}
            </span>
          )}
          {result.placeAddress && (
            <span className="meta-with-icon">
              <MapPinIcon size={13} />
              {result.placeAddress}
            </span>
          )}
        </div>
      </div>
    </article>
  );
}
