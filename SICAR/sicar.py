class Sicar(Url):
    def __init__(self, driver: Captcha = Tesseract, headers: Dict = None):
        self._driver = driver()
        self._client = HttpClient(verify_ssl=False)
        if headers:
            self._client.set_headers(headers)
        self._initialize_cookies()

    def _initialize_cookies(self):
        """Initialize cookies by making the initial request"""
        try:
            self._client.get(self._INDEX)
        except Exception as e:
            self._logger.warning(f"Cookie initialization failed: {str(e)}")

    def get_release_dates(self) -> Dict:
        try:
            response = self._client.get(self._RELEASE_DATE)
            return self._parse_release_dates(response.content)
        except Exception as error:
            raise FailedToGetReleaseDateException() from error

    def _download_captcha(self) -> Image:
        """Download captcha image"""
        try:
            url = f"{self._RECAPTCHA}?{urlencode({'id': int(random.random() * 1000000)})}"
            response = self._client.get(url)
            return Image.open(io.BytesIO(response.content))
        except Exception as error:
            self._logger.error(f"Failed to download captcha: {str(error)}")
            raise FailedToDownloadCaptchaException() from error

    def download_state(self, state: State | str, polygon: Polygon | str, 
                      folder: Path | str = Path("temp"), tries: int = 25,
                      debug: bool = False, chunk_size: int = 1024) -> Path | bool:
        if isinstance(state, str):
            try:
                state = State(state.upper())
            except ValueError as error:
                raise StateCodeNotValidException(state) from error

        if isinstance(polygon, str):
            try:
                polygon = Polygon(polygon.upper())
            except ValueError as error:
                raise PolygonNotValidException(polygon) from error

        Path(folder).mkdir(parents=True, exist_ok=True)
        info = f"'{polygon.value}' for '{state.value}'"

        while tries > 0:
            try:
                captcha = self._driver.get_captcha(self._download_captcha())
                if len(captcha) == 5:
                    if debug:
                        print(f"[{tries:02d}] - Requesting {info} with captcha '{captcha}'")
                    return self._download_polygon(
                        state=state,
                        polygon=polygon,
                        captcha=captcha,
                        folder=folder,
                        chunk_size=chunk_size
                    )
                elif debug:
                    print(f"[{tries:02d}] - Invalid captcha '{captcha}' to request {info}")
            except Exception as error:
                if debug:
                    print(f"[{tries:02d}] - {error} When requesting {info}")
            finally:
                tries -= 1
                time.sleep(random.random() + random.random())

        return False

    def __del__(self):
        """Cleanup resources"""
        self._client.close()