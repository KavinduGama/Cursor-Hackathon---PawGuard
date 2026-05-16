import { ClinicIcon, HomeIcon, MapPinIcon, PhoneIcon } from './AppIcons.jsx';

export default function ResultCard({ result }) {
  const status = (result.status || 'in_progress').toLowerCase();
  const isVet = result.kind === 'vet';
  const label = isVet ? 'Vet clinic call' : 'Foster care call';
  const Icon = isVet ? ClinicIcon : HomeIcon;
  const successfulPlace = result.successful_place || {};
  const placeName = result.placeName || successfulPlace.name;
  const placePhone = result.placePhone || successfulPlace.phone;
  const placeAddress = result.placeAddress || successfulPlace.address;
  const placeLat = result.placeLat ?? successfulPlace.lat;
  const placeLng = result.placeLng ?? successfulPlace.lng;
  const hasCoords = Number.isFinite(Number(placeLat)) && Number.isFinite(Number(placeLng));
  const destination = hasCoords
    ? `${placeLat},${placeLng}`
    : placeAddress || placeName || '';
  const mapUrl = destination
    ? `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}`
    : '';

  return (
    <article className={`card call-card ${isVet ? 'vet' : 'foster'}`}>
      <div className="icon-wrap" aria-hidden>
        <Icon size={20} />
      </div>
      <div className="body">
        <div className="row">
          <span className="title">{placeName || 'Calling…'}</span>
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
          {result.contact_name && <span>{result.contact_name}</span>}
          {result.wait_minutes != null && (
            <span>~{result.wait_minutes} min</span>
          )}
          {placePhone && (
            <span className="meta-with-icon">
              <PhoneIcon size={13} />
              {placePhone}
            </span>
          )}
          {placeAddress && (
            <span className="meta-with-icon">
              <MapPinIcon size={13} />
              {placeAddress}
            </span>
          )}
        </div>
        {mapUrl && result.available === true && (
          <a
            className="btn btn-primary btn-block map-directions-btn"
            href={mapUrl}
            target="_blank"
            rel="noreferrer"
          >
            Open directions in Google Maps
          </a>
        )}
      </div>
    </article>
  );
}
