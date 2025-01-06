        for path, _, im0s, vid_cap, s in self.dataset:
            # Inference
            with dt[0]:
                pred = self.get_face_detects(im0s)

            all_cropped_faces = []
            metadata = []
            face_counts = []

            # Crop all faces
            for i, det in enumerate(pred):
                if self.media_manager.webcam:  
                    im0 = im0s[i].copy()
                else:
                    im0 = im0s.copy()

                if det is None:
                    face_counts.append(0)
                    continue
                
                bboxes, keypoints = det
                for bbox, kps in zip(bboxes, keypoints):
                    metadata.append({
                        "image_index": i,
                        "bbox": bbox,
                        "keypoints": kps
                    })

                if self.media_manager.face_recognition:
                    cropped_faces = crop_and_align_faces(im0, bboxes, keypoints, 0.7)
                    all_cropped_faces.extend(cropped_faces)
                face_counts.append(len(bboxes))
            
            # for crop in all_cropped_faces:
            #     print(len(all_cropped_faces))
            #     print(is_real_face(img=crop, threshold=0.65))
            # print("================================")

            # Search ids, emotion analysis
            ids = []
            emotions = []
            with dt[1]:
                if self.media_manager.face_recognition and all_cropped_faces:
                    all_embeddings = self.get_face_embeddings(all_cropped_faces)
                    ids = search_ids_mongoDB(all_embeddings, top_k=1, threshold=0.5)

                    if self.media_manager.raise_hand or self.media_manager.check_small_face:
                        start_idx = 0

                        for img_index, im0 in enumerate(im0s):
                            if self.media_manager.webcam:  
                                im0 = im0s[i].copy()
                            else:
                                im0 = im0s.copy()
                            
                            metadata_for_image = [meta for meta in metadata if meta["image_index"] == img_index]
                            ids_for_image = ids[start_idx:start_idx + len(metadata_for_image)] if self.media_manager.face_recognition else []

                            for meta, id_info in zip(metadata_for_image, ids_for_image):
                                bbox = np.array(meta["bbox"][:4], dtype=int)

                                if id_info:

                                    if self.media_manager.face_emotion:
                                        emotion = self.fer_class.get_dominant_emotion(self.fer_class.analyze_face(im0, bbox))[0]
                                        emotions.append(emotion)

                                    if self.media_manager.raise_hand:
                                        cropped_expand_image = expand_and_crop_image(im0, bbox, left=2.6, right=2.6, top=1.6, bottom=2.6)

                                        if is_hand_opened_in_image(cropped_expand_image) and is_person_raising_hand_image(cropped_expand_image):
                                            camera_name = self.media_manager.camera_names[img_index]
                                            message = f"Học sinh {id_info[0]['full_name']} giơ tay! [{camera_name}]"
                                            send_notification(message)

                                    # --------------------------------------------------------------------------------
                                    print("DEBUG SMALL FACE INFO")
                                    print(id_info)
                                    cropped_image = crop_image(im0, bbox)
                                    print("Shape of cropped_image:", cropped_image.shape)
                                    restored_img = self.gfpgan_model.inference(cropped_image)
                                    print("Shape of restored_img:", restored_img.shape)
                                    embedding = self.get_face_embeddings(restored_img)
                                    id = search_ids_mongoDB(embedding, top_k=1, threshold=0.5)
                                    print("ID sau khi lam net:", id)
                                    cv2.imshow("Restored image", restored_img)
                                    cv2.waitKey(0)
                                    # --------------------------------------------------------------------------------
                                else:
                                    if self.media_manager.check_small_face and is_small_face(bbox=bbox, min_size=50):
                                        cropped_image = crop_image(im0, bbox)
                                        print("Shape of cropped_image:", cropped_image.shape)
                                        restored_img = self.gfpgan_model.inference(cropped_image)
                                        print("Shape of restored_img:", restored_img.shape)
                                        embedding = self.get_face_embeddings(restored_img)
                                        id = search_ids_mongoDB(embedding, top_k=1, threshold=0.5)
                                        print(id)
                                        print("DEBUG SMALL FACE")
                                        cv2.imshow("Restored image", restored_img)
                                        cv2.waitKey(0)

                                    emotions.append(None)
                            start_idx += len(metadata_for_image)