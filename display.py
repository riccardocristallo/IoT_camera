import cv2

class Display:
    def __init__(self, window_name="IoT Camera"):
        self.window_name = window_name

    def show(self, frame, num_persons, num_with_phone):
        cv2.putText(frame, f"Persons: {num_persons}  |  With phone: {num_with_phone}",
                    (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        if num_with_phone > 0:
            cv2.putText(frame, "PHONE DETECTED!", (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        cv2.imshow(self.window_name, frame)

    def should_quit(self):
        return cv2.waitKey(1) & 0xFF == ord('q')

    def close(self):
        cv2.destroyAllWindows()